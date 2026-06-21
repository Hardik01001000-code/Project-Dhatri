# Project Dhatri

Project Dhatri is a microservices-based AI assistant system. It integrates vision, listening, and speaking capabilities using advanced machine learning models.

## Architecture

The project consists of several microservices and components:
- **Vision Microservice**: Handles camera input, facial recognition, and image-based AI interactions.
- **Listen Microservice**: Manages audio input and speech-to-text using Faster-Whisper.
- **Speak Microservice**: Handles text-to-speech generation.
- **GUI**: The user interface for the assistant.

## Setup Instructions

### Prerequisites
- Python 3.9+
- A CUDA-capable GPU is highly recommended for running the AI models efficiently.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Hardik01001000-code/Project-Dhatri.git
   cd Project-Dhatri
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - **Windows:**
     ```cmd
     venv\Scripts\activate
     ```
   - **Linux/macOS:**
     ```bash
     source venv/bin/activate
     ```

4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

To start the main application, run:
```bash
python main.py
```

## Notice Regarding AI Models
Due to the large size of AI model weights, they are excluded from this repository. When you run the respective microservices for the first time, they may attempt to automatically download the required models into their respective directories (e.g., `listen_microservice/models/` and `speak_microservice/checkpoints_v2/`).
