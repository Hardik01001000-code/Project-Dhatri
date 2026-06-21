import os
from tts_engine import TTSEngine

def test_tts():
    print("Initializing TTS Engine...")
    engine = TTSEngine()
    
    # 1. Generate a dummy reference audio using MeloTTS directly to use as target speaker
    # (Since we don't have a real reference audio, we just use MeloTTS base voice for testing the pipeline)
    print("Generating reference audio...")
    ref_audio_path = "test_reference.wav"
    long_ref_text = "This is a reference voice for testing the voice cloning. We need to make sure this sentence is long enough for the OpenVoice engine to extract speaker characteristics successfully. It requires a few seconds of audio data to build a good speaker embedding vector. Hopefully this paragraph is long enough."
    engine.melo_tts.tts_to_file(long_ref_text, engine.default_spkr, ref_audio_path)
    
    # 2. Run the generation pipeline
    output_path = "test_output.wav"
    text_to_generate = "Hello! This is a test of the text to speech microservice. We are verifying the voice cloning capability."
    print("Generating final speech...")
    engine.generate(text_to_generate, ref_audio_path, output_path)
    print(f"Success! Output saved to {output_path}")

if __name__ == "__main__":
    test_tts()
