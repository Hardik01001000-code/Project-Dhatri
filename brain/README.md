# 🧠 Brain Microservice

The **Brain Microservice** serves as the central reasoning and prompt-processing hub for Project Dhatri. It processes input text (received via typed user input or transcribed speech from the Listen Microservice) and generates responses that are routed to the Speak Microservice for audio synthesis.

---

## 🚀 Current Status

- **Mode:** Echo / Pass-through
- **Behavior:** Takes user prompt text and returns the exact same text, forwarding it to the **Speak Microservice** for immediate voice-cloned speech synthesis.
- **Extensible:** Designed to plug in local LLMs (e.g., Llama, Mistral, Phi via Ollama or llama.cpp) seamlessly in place of `process_prompt`.

---

## 🛠️ Usage

### 1. Interactive Standalone CLI
To test the Brain microservice directly in the terminal hooked up to the Speak microservice:

```bash
python -m brain
# or
python brain/main.py
```

Type any text and hit **Enter**:
```text
You > Hello Dhatri
Brain > Hello Dhatri
[Speak Microservice] Speaking: "Hello Dhatri"...
```

### 2. Desktop GUI
Run the main desktop application:

```bash
python main.py
```

When you type a message in the chat input bar and hit **Enter** (or send a voice command):
1. The prompt is sent to `brain.core.process_prompt()`.
2. The Brain returns the processed output.
3. The response is displayed as an assistant message in the chat canvas.
4. The response is concurrently synthesized and spoken aloud by `SpeakThread` via MeloTTS and OpenVoice V2.

---

## 📁 File Structure

```text
brain/
├── __init__.py      # Package initialization exposing process_prompt
├── __main__.py      # CLI entrypoint for `python -m brain`
├── core.py          # Core reasoning logic (process_prompt)
├── main.py          # Standalone CLI connecting Brain -> Speak
└── README.md        # This file
```
