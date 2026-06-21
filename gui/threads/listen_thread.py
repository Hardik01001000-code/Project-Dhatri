import threading
import queue
from PyQt6.QtCore import QThread, pyqtSignal

class ListenThread(QThread):
    state_signal = pyqtSignal(str)
    text_signal = pyqtSignal(str)
    rms_signal = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.shutdown_event = threading.Event()
        self.state_queue = queue.Queue()

    def run(self):
        try:
            from listen_microservice.main import listen_worker
        except ImportError as e:
            print(f"[Dhatri Listen] Error importing listen microservice: {e}")
            return

        worker_thread = threading.Thread(
            target=listen_worker,
            args=(self.shutdown_event, self.state_queue),
            daemon=True
        )
        worker_thread.start()

        while not self.shutdown_event.is_set():
            try:
                msg = self.state_queue.get(timeout=0.1)
                if msg["type"] == "STATE":
                    self.state_signal.emit(msg["value"])
                elif msg["type"] == "TEXT":
                    self.text_signal.emit(msg["value"])
                elif msg["type"] == "RMS":
                    self.rms_signal.emit(msg["value"])
            except queue.Empty:
                pass
            
        worker_thread.join(timeout=1.0)

    def stop(self):
        self.shutdown_event.set()
        self.wait()
