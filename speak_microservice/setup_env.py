import os
import urllib.request
import zipfile

def download_openvoice_v2_checkpoints():
    """
    Downloads the OpenVoice V2 checkpoints ZIP from the Hugging Face mirror and extracts it.
    """
    url = "https://huggingface.co/cqchangm/openvoice2/resolve/main/checkpoints_v2_0417.zip"
    
    base_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else "."
    zip_path = os.path.join(base_dir, "checkpoints_v2_0417.zip")
    extract_dir = os.path.join(base_dir, "checkpoints_v2")
    
    print(f"Downloading OpenVoice V2 checkpoints from {url}...")
    # Add a user-agent to avoid HTTP 403 errors sometimes
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
        data = response.read() # Might be large, but acceptable for a quick script
        out_file.write(data)
    
    print("Download complete. Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Extract contents. Note: The zip might contain a root 'checkpoints_v2' folder,
        # or just the contents. We will extract to base_dir, and if it creates a checkpoints_v2 folder, we're good.
        # Alternatively we can inspect its contents.
        # usually it contains a `checkpoints_v2` folder.
        zip_ref.extractall(base_dir)
        
    print(f"Extracted to {base_dir}")
    
    # Clean up zip
    if os.path.exists(zip_path):
        os.remove(zip_path)

if __name__ == "__main__":
    download_openvoice_v2_checkpoints()

