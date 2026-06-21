import os
import sys
import shutil
from pathlib import Path

def set_default_voice(new_audio_path):
    """
    Sets the default voice for the TTS microservice by copying the provided audio file
    to 'default_voice.wav'. This will be automatically used by main.py.
    """
    if not os.path.exists(new_audio_path):
        print(f"Error: The file {new_audio_path} does not exist.")
        sys.exit(1)
        
    # Check if the file is a valid audio file (basic extension check)
    valid_extensions = ['.wav', '.mp3', '.flac', '.ogg']
    ext = Path(new_audio_path).suffix.lower()
    if ext not in valid_extensions:
        print(f"Warning: The file extension '{ext}' might not be supported.")
        print(f"Supported extensions usually include: {', '.join(valid_extensions)}")
        
    print(f"Setting default voice to: {new_audio_path}")
    
    # Destination path
    target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "default_voice.wav")
    
    try:
        shutil.copy2(new_audio_path, target_path)
        print("Success! The default voice has been updated.")
        print("Note: Make sure the audio clip is clear and at least 5-10 seconds long for best cloning results.")
    except Exception as e:
        print(f"Error copying file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python set_default_voice.py <path_to_audio_file>")
        print("Example: python set_default_voice.py new_voice_sample.wav")
        sys.exit(1)
        
    set_default_voice(sys.argv[1])
