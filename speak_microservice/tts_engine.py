import os
import hashlib
import torch
import warnings
import io
import soundfile
from pathlib import Path

# Enforce strictly offline behavior for HuggingFace downloads
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Intercept subprocess.run to use the absolute path to imageio-ffmpeg's binary
try:
    import imageio_ffmpeg
    import subprocess
    original_run = subprocess.run
    def patched_run(*args, **kwargs):
        if len(args) > 0 and isinstance(args[0], list) and len(args[0]) > 0 and args[0][0] == "ffmpeg":
            args[0][0] = imageio_ffmpeg.get_ffmpeg_exe()
        return original_run(*args, **kwargs)
    subprocess.run = patched_run
except ImportError:
    pass

# Suppress some noisy warnings from dependencies
warnings.filterwarnings("ignore")

from melo.api import TTS
from openvoice.api import ToneColorConverter
from openvoice import se_extractor

class TTSEngine:
    def __init__(self, checkpoints_dir=None, cache_dir=None, preload_voice=None):
        """
        Initialize the TTS Engine with OpenVoice V2 and MeloTTS.

        Args:
            checkpoints_dir: Path to OpenVoice V2 checkpoints. Defaults to ./checkpoints_v2.
            cache_dir: Path for speaker embedding cache. Defaults to ./embeddings_cache.
            preload_voice: Optional path to a reference audio file. If provided, the speaker
                           embedding is extracted/loaded at init time instead of on first call,
                           moving the cold-start penalty to boot time.
        """
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.checkpoints_dir = checkpoints_dir or os.path.join(base_dir, "checkpoints_v2")
        self.cache_dir = cache_dir or os.path.join(base_dir, "embeddings_cache")
        
        os.makedirs(self.cache_dir, exist_ok=True)
        os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
        import logging
        logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)
        
        try:
            self.device = "cuda:0" if torch.cuda.is_available() and torch.cuda.device_count() > 0 else "cpu"
        except Exception:
            self.device = "cpu"
        self._use_fp16 = self.device.startswith("cuda")
        print(f"Initializing TTSEngine on {self.device} (FP16={self._use_fp16})...")
        
        # 1. Initialize MeloTTS for English base audio generation
        self.melo_tts = TTS(language='EN', device=self.device)
        self.speaker_ids = self.melo_tts.hps.data.spk2id
        # Access EN-US speaker ID (spk2id may be an HParams object, so use attribute or dictionary access safely)
        try:
            self.default_spkr = self.speaker_ids['EN-US']
        except TypeError:
            self.default_spkr = getattr(self.speaker_ids, 'EN-US', list(self.speaker_ids.values())[0] if hasattr(self.speaker_ids, 'values') else 0)
        
        # 2. Initialize ToneColorConverter
        converter_ckpt = os.path.join(self.checkpoints_dir, "converter")
        config_path = os.path.join(converter_ckpt, "config.json")
        checkpoint_path = os.path.join(converter_ckpt, "checkpoint.pth")
        
        if not os.path.exists(config_path) or not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"ToneColorConverter checkpoint not found in {converter_ckpt}")
            
        self.tone_color_converter = ToneColorConverter(config_path, device=self.device)
        self.tone_color_converter.load_ckpt(checkpoint_path)
        
        # OpenVoice has a bug where passing enable_watermark=False crashes the parent class.
        # Instead, we let it initialize, then forcefully delete the watermark model to free VRAM.
        if hasattr(self.tone_color_converter, 'watermark_model') and self.tone_color_converter.watermark_model is not None:
            del self.tone_color_converter.watermark_model
            self.tone_color_converter.watermark_model = None
            if self.device.startswith("cuda"):
                torch.cuda.empty_cache()
        
        # 3. Load Base Speaker Embedding (Source SE)
        # In V2, base speaker embeddings are pre-computed .pth files
        base_se_path = os.path.join(self.checkpoints_dir, "base_speakers", "ses", "en-us.pth")
        if not os.path.exists(base_se_path):
            raise FileNotFoundError(f"Base speaker embedding not found at {base_se_path}")
            
        self.source_se = self._safe_torch_load(base_se_path, self.device)

        # 4. Pre-warm the speaker embedding cache if a voice path was provided
        if preload_voice and os.path.exists(preload_voice):
            print(f"Pre-warming speaker embedding for: {preload_voice}")
            try:
                self.get_target_speaker_embedding(preload_voice)
            except Exception as e:
                print(f"Warning: Failed to pre-warm voice embedding: {e}")

        print("TTSEngine initialization complete.")

    @staticmethod
    def _safe_torch_load(path, device):
        """Load a tensor checkpoint safely, compatible with PyTorch >=2.0 and older versions."""
        try:
            return torch.load(path, map_location=device, weights_only=True).to(device)
        except TypeError:
            # Older PyTorch versions don't support weights_only
            return torch.load(path, map_location=device).to(device)

    def _get_file_hash(self, filepath):
        """Compute MD5 hash of a file for caching purposes."""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def get_target_speaker_embedding(self, ref_audio_path):
        """
        Extract the target speaker embedding from the reference audio.
        Uses caching to avoid redundant extraction and optimize latency.
        """
        if not os.path.exists(ref_audio_path):
            raise FileNotFoundError(f"Reference audio not found: {ref_audio_path}")
            
        audio_hash = self._get_file_hash(ref_audio_path)
        cache_path = os.path.join(self.cache_dir, f"{audio_hash}.pt")
        
        if os.path.exists(cache_path):
            print(f"Loading speaker embedding from cache: {cache_path}")
            target_se = self._safe_torch_load(cache_path, self.device)
            return target_se
            
        print(f"Extracting new speaker embedding for: {ref_audio_path}")
        target_dir = os.path.join(self.cache_dir, "processed")
        os.makedirs(target_dir, exist_ok=True)
        
        # Extract target_se using OpenVoice
        try:
            target_se, audio_name = se_extractor.get_se(
                ref_audio_path, 
                self.tone_color_converter, 
                target_dir=target_dir, 
                vad=True
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to extract speaker embedding from '{ref_audio_path}'. "
                f"The audio may be too short, corrupt, or in an unsupported format. "
                f"Original error: {e}"
            ) from e
        
        # target_se is typically a tensor
        # Move it to correct device and save to cache
        target_se = target_se.to(self.device)
        torch.save(target_se, cache_path)
        print(f"Saved speaker embedding to cache: {cache_path}")
        
        return target_se

    def generate(self, text, ref_audio_path, output_path=None, speed=1.0):
        """
        Generate cloned speech from text using the reference audio.
        If output_path is None, returns (sample_rate, audio_numpy_array) for direct memory streaming.
        """
        target_se = self.get_target_speaker_embedding(ref_audio_path)
        
        # torch.no_grad() covers the entire pipeline to skip autograd bookkeeping.
        # NOTE: autocast is only applied to the voice conversion step, NOT MeloTTS.
        # MeloTTS uses rational quadratic spline transforms that are numerically
        # unstable in FP16 (discriminant goes negative → assertion failure).
        with torch.no_grad():
            # 1. Generate base audio using MeloTTS (must stay FP32)
            base_audio = self.melo_tts.tts_to_file(text, self.default_spkr, output_path=None, speed=speed)
            
            # 2. Write base_audio to memory buffer to pass to ToneColorConverter
            buffer = io.BytesIO()
            soundfile.write(buffer, base_audio, self.melo_tts.hps.data.sampling_rate, format='WAV')
            buffer.seek(0)
            
            # 3. Convert Tone Color (Voice Cloning) — autocast for mixed-precision speedup
            if output_path is not None:
                print(f"Applying voice cloning to generate: {output_path}")
                os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            else:
                print("Applying voice cloning in-memory for direct streaming...")
                
            with torch.amp.autocast(device_type="cuda", enabled=self._use_fp16):
                output_audio = self.tone_color_converter.convert(
                    audio_src_path=buffer,
                    src_se=self.source_se,
                    tgt_se=target_se,
                    output_path=output_path,
                    message="@MyShell"
                )
            
        if output_path is None:
            return self.tone_color_converter.hps.data.sampling_rate, output_audio
        return output_path

    def generate_stream(self, text, ref_audio_path, speed=1.0):
        """
        Generate cloned speech from text as a stream of audio chunks.
        Splits text into sentences, processes each, and yields (sample_rate, numpy_audio) immediately.
        Ideal for real-time conversational AI.
        """
        target_se = self.get_target_speaker_embedding(ref_audio_path)
        
        # Split text into sentences for streaming
        texts = self.melo_tts.split_sentences_into_pieces(text, self.melo_tts.language, quiet=True)
        sample_rate = self.tone_color_converter.hps.data.sampling_rate
        
        # torch.no_grad() covers the loop. MeloTTS must run in FP32 (no autocast)
        # to prevent assertion failure in rational_quadratic_spline.
        with torch.no_grad():
            for t in texts:
                if not t.strip():
                    continue
                    
                # 1. Generate base audio for the sentence (in FP32)
                base_audio = self.melo_tts.tts_to_file(t, self.default_spkr, output_path=None, speed=speed)
                
                # 2. Write to memory buffer
                buffer = io.BytesIO()
                soundfile.write(buffer, base_audio, self.melo_tts.hps.data.sampling_rate, format='WAV')
                buffer.seek(0)
                
                # 3. Clone voice in-memory with mixed-precision autocast
                with torch.amp.autocast(device_type="cuda", enabled=self._use_fp16):
                    output_audio = self.tone_color_converter.convert(
                        audio_src_path=buffer,
                        src_se=self.source_se,
                        tgt_se=target_se,
                        output_path=None,
                        message="@MyShell"
                    )
                    
                yield sample_rate, output_audio

if __name__ == "__main__":
    # Example usage / Test logic
    pass
