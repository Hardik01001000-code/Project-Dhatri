import os
import sys

def main():
    os.makedirs("./models", exist_ok=True)
    print("Downloading YOLO11s model for high accuracy...")
    try:
        from ultralytics import YOLO
        # This automatically downloads the weights from Ultralytics servers
        model = YOLO("./models/yolo11s.pt")
        print("Successfully downloaded yolo11s.pt to ./models/!")
    except Exception as e:
        print(f"Failed to download YOLO11s model: {e}")
        sys.exit(1)
        
    print("Pre-downloading/verifying face_recognition assets (if any are lazily loaded)...")
    try:
        import face_recognition
        print("Successfully imported face_recognition. Default models are available.")
    except ImportError as e:
        print(f"face_recognition not installed yet or failed to import. {e}")
        
    print("Asset setup complete!")

if __name__ == "__main__":
    main()
