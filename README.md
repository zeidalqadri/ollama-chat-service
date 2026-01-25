# BÖRAK01 - Private Inference Facility

Private AI assistant powered by open-source models. Zero telemetry, sovereign data.

## Access

**Live:** https://alumist.alumga.com/borak01/

## Quick Start

1. Click **Register** tab → create account
2. Switch to **Login** → sign in
3. Start chatting

## Available Models

| Model | Size | Purpose |
|-------|------|---------|
| **qwen3-coder:30b** | 18 GB | Code generation, debugging, refactoring |
| **stable-beluga:13b** | 7.4 GB | Creative writing, storytelling |
| **gnokit/improve-prompt** | 1.6 GB | Prompt optimization for image gen |
| **deepseek-ocr** | 6.7 GB | Vision/OCR - image understanding |

Select from the sidebar dropdown.

## Features

- Session management (multiple chat threads)
- Artifacts panel (code snippets, thoughts, explanations)
- Stop/continue generation controls
- Image upload for vision models
- Mobile-optimized responsive design
- Syntax highlighting for code blocks
- No usage limits, completely private

## Mobile Support

Works on iPhone, Android, and tablets:
- Swipe-in sidebar
- Bottom sheet for artifacts
- Touch-friendly 44px targets

## Tips

### Code Generation
```
Write a Python function that validates email addresses.
Include type hints and docstring.
```

### Prompt Optimization
Select `improve-prompt` model:
```
a cat sitting on a chair
```
→ Returns detailed, evocative prompt for image generation

### Creative Writing
Select `stable-beluga:13b`:
```
Write the opening paragraph of a noir detective story.
```

## Architecture

```
Browser → Nginx (reverse proxy) → FastAPI (port 8012) → Ollama (localhost:11434)
                                       ↓
                              SQLite + ChromaDB
```

## Self-Hosting

```bash
# Clone
git clone https://github.com/zeidalqadri/ollama-chat-service.git
cd ollama-chat-service

# Install
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
uvicorn main:app --host 0.0.0.0 --port 8012
```

Requires Ollama running on `localhost:11434`.

## Support

Contact: **zeidalqadri**

---

*E2E Encrypted // Zero Telemetry // Sovereign Data*
