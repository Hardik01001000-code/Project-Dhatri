import os
import sys

def main():
    os.makedirs("./models", exist_ok=True)
    print("Downloading YOLO26n model...")
    try:
        from ultralytics import YOLO
        # This automatically downloads the weights from Ultralytics servers
        model = YOLO("./models/yolo26n.pt")
        print("Successfully downloaded yolo26n.pt to ./models/!")
    except Exception as e:
        print(f"Failed to download YOLO26n model: {e}")
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
