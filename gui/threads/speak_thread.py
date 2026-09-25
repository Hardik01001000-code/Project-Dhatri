from PyQt6.QtCore import QThread, pyqtSignal
import queue
import threading
import os

class SpeakThread(QThread):
    # Signals for the GUI to react to speaking state changes
    speaking_started = pyqtSignal()
    speaking_finished = pyqtSignal()

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

    def _audio_player_worker(self, audio_queue, sd):
        """
        Background worker that continuously plays audio chunks from the queue.
        Runs in a dedicated daemon thread so TTS generation and audio playback
        are pipelined — the next chunk is being generated while the current one plays.
        """
        while True:
            item = audio_queue.get()
            if item is None:  # Poison pill to exit
                audio_queue.task_done()
                break

            sample_rate, chunk = item
            try:
                sd.play(chunk, sample_rate)
                sd.wait()
            except Exception as e:
                print(f"[Dhatri Speak] Playback error in worker: {e}")
            audio_queue.task_done()

    def run(self):
        try:
            from speak_microservice.tts_engine import TTSEngine
            import sounddevice as sd
        except ImportError as e:
            print(f"[Dhatri Speak] Error importing TTS engine or sounddevice: {e}")
            return

        # Validate default voice exists before initializing the engine
        if not os.path.exists(self.default_voice_path):
            fallback_voice = os.path.join(
                os.path.dirname(self.default_voice_path), "test_reference.wav"
            )
            if os.path.exists(fallback_voice):
                import shutil
                print(f"[Dhatri Speak] Setting default voice from {fallback_voice}")
                shutil.copyfile(fallback_voice, self.default_voice_path)
            else:
                print(f"[Dhatri Speak] ERROR: default_voice.wav not found at {self.default_voice_path}")
                print("[Dhatri Speak] Run set_default_voice.py to configure a voice first.")
                return

        print("[Dhatri Speak] Initializing TTS Engine...")
        try:
            # Pre-warm the speaker embedding cache at boot time
            self.engine = TTSEngine(preload_voice=self.default_voice_path)
        except Exception as e:
            print(f"[Dhatri Speak] Error starting TTS Engine: {e}")
            return

        print("[Dhatri Speak] TTS Engine ready!")

        # Create a persistent audio playback queue and worker thread.
        # This is the double-buffer pattern: the SpeakThread generates chunks into
        # the queue while the player thread consumes and plays them concurrently.
        # This eliminates silence gaps between sentences.
        audio_queue = queue.Queue(maxsize=4)  # Small buffer to limit memory; blocks when full
        player_thread = threading.Thread(
            target=self._audio_player_worker, args=(audio_queue, sd), daemon=True
        )
        player_thread.start()

        while self._run_flag:
            try:
                text = self.text_queue.get(timeout=0.1)
                if text is None:
                    break

                if not text or not str(text).strip():
                    continue

                if self.is_muted:
                    continue

                self.speaking_started.emit()
                try:
                    for sample_rate, audio_chunk in self.engine.generate_stream(text, self.default_voice_path):
                        if not self._run_flag or self.is_muted:
                            break
                        audio_queue.put((sample_rate, audio_chunk))

                    # Wait for all queued chunks to finish playing before signaling done
                    audio_queue.join()
                except Exception as e:
                    print(f"[Dhatri Speak] Error during generation/playback: {e}")
                finally:
                    self.speaking_finished.emit()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Dhatri Speak] Error during playback: {e}")

        # Shut down the player thread cleanly
        audio_queue.put(None)
        player_thread.join(timeout=5)

    def stop(self):
        self._run_flag = False
        self.text_queue.put(None)
        self.wait()
