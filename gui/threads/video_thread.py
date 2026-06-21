from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(QImage)

    def __init__(self):
        super().__init__()
        self._run_flag = True

    def run(self):
        try:
            from vision_microservice import main_vision_service as vms
        except ImportError as e:
            print(f"[Dhatri Vision] Error importing vision microservice: {e}")
            return
            
        print("[Dhatri Vision] Connecting to Vision Microservice...", flush=True)
            
        vms.start_workers()
        
        print("[Dhatri Vision] Subscribed to vision data stream.", flush=True)

        while self._run_flag:
            frame = vms.get_annotated_frame(timeout=0.1)
            if frame is None:
                continue

            h, w, ch = frame.shape
            bytes_per_line = ch * w
            
            qt_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
            self.change_pixmap_signal.emit(qt_img.copy())
            
        print("[Dhatri Vision] Stopping microservice threads...", flush=True)
        vms.stop_workers()
        print("[Dhatri Vision] Camera released by microservice.", flush=True)

    def stop(self):
        self._run_flag = False
        self.wait()
