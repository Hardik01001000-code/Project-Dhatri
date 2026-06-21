from PyQt6.QtCore import QThread, pyqtSignal
import queue
import os

class SpeakThread(QThread):
    def __init__(self):
        super().__init__()
        self.text_queue = queue.Queue()
        self._run_flag = True
        self.engine = None
        self.default_voice_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "speak_microservice", "default_voice.wav"
        )
        self.is_muted = False

    def speak(self, text):
        if not self.is_muted:
            self.text_queue.put(text)

    def set_muted(self, muted: bool):
        self.is_muted = muted
        if muted:
            # Clear the queue so it stops pending speeches
            while not self.text_queue.empty():
                try:
                    self.text_queue.get_nowait()
                except queue.Empty:
                    break

    def run(self):
        try:
            from speak_microservice.tts_engine import TTSEngine
            import sounddevice as sd
        except ImportError as e:
            print(f"[Dhatri Speak] Error importing TTS engine or sounddevice: {e}")
            return

        print("[Dhatri Speak] Initializing TTS Engine...")
        try:
            self.engine = TTSEngine()
        except Exception as e:
            print(f"[Dhatri Speak] Error starting TTS Engine: {e}")
            return

        print("[Dhatri Speak] TTS Engine ready!")

        while self._run_flag:
            try:
                text = self.text_queue.get(timeout=0.1)
                if text is None:
                    break

                if self.is_muted:
                    continue

                for sample_rate, audio_chunk in self.engine.generate_stream(text, self.default_voice_path):
                    if not self._run_flag or self.is_muted:
                        break
                    sd.play(audio_chunk, sample_rate)
                    sd.wait()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Dhatri Speak] Error during playback: {e}")

    def stop(self):
        self._run_flag = False
        self.text_queue.put(None)
        self.wait()
