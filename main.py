import sys
import os
import subprocess

# --- Auto-Relaunch into Virtual Environment ---
venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "Scripts", "python.exe")
if os.path.exists(venv_python) and sys.executable.lower() != venv_python.lower():
    print(f"[Dhatri Setup] Relaunching app using virtual environment...")
    sys.exit(subprocess.call([venv_python] + sys.argv))
# ----------------------------------------------

import os
import sys
import subprocess

# Test if the CUDA environment is fully working in an isolated subprocess
# If the user is missing DLLs like cublas64_12.dll, this will fail and we can safely fallback to CPU
# BEFORE we import torch in the main process (torch only reads CUDA_VISIBLE_DEVICES at import time).
try:
    test_code = "import torch; torch.matmul(torch.randn(2, 2, device='cuda'), torch.randn(2, 2, device='cuda'))"
    # Suppress output to keep console clean
    print("[Dhatri Setup] Testing CUDA environment... (This may take up to 30 seconds on the first run)")
    result = subprocess.run([sys.executable, "-c", test_code], capture_output=True, timeout=30)
    if result.returncode != 0:
        print(f"[Dhatri Setup] Warning: CUDA environment is broken or missing DLLs. Falling back to CPU.")
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
except Exception as e:
    print(f"[Dhatri Setup] Warning: CUDA test failed ({e}). Falling back to CPU.")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

# Must be imported after the environment is potentially re-launched
import torch
# Pre-initialize PyTorch CUDA in the main thread to prevent multi-threading initialization crashes on Windows.
if torch.cuda.is_available():
    _ = torch.tensor([1.0]).cuda()

from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
