# Ollama Chat Service

Private AI coding assistant powered by open-source models. Free to use, no API costs.

## Quick Start

### 1. Access the Chat UI

🔗 **http://45.159.230.42:8501**

### 2. Create an Account

1. Click the **Register** tab
2. Choose a username and password (min 6 characters)
3. Click **Register**
4. Switch to **Login** tab and sign in

### 3. Start Chatting

- Type your message in the input box
- Press Enter or click Send
- Wait for the AI response (10-30 seconds on CPU)

## Available Models

| Model | Best For | Context |
|-------|----------|---------|
| qwen3-coder:30b | Code generation, debugging, refactoring | 256K tokens |
| qwen2.5-coder:14b | Faster responses, general coding | 128K tokens |

Select your model from the sidebar dropdown.

## Tips for Best Results

### Code Generation
```
Write a Python function that validates email addresses using regex.
Include type hints and docstring.
```

### Debugging
```
Here's my code that's throwing an error:
[paste code]

Error message:
[paste error]

What's wrong and how do I fix it?
```

### Code Review
```
Review this code for potential issues:
[paste code]

Focus on: security, performance, readability
```

### Refactoring
```
Refactor this function to be more readable and maintainable:
[paste code]
```

## Features

- ✅ Chat history (within session)
- ✅ Multiple model selection
- ✅ Code syntax highlighting
- ✅ No usage limits
- ✅ Private - data stays on our server

## Limitations

- ⚠️ CPU inference - responses take 10-30 seconds
- ⚠️ Chat history clears on page refresh
- ⚠️ Single conversation thread (no branching)
- ⚠️ No file upload (paste code directly)

## For Power Users (CLI Access)

If you need direct API access for tools like Aider, contact the admin to whitelist your IP.

### Using with Aider

Once whitelisted:

```bash
# Install Aider
uv tool install aider-chat

# Set environment variable
export OLLAMA_API_BASE=http://45.159.230.42:11434

# Run in your project
cd your-project
aider --model ollama/qwen3-coder:30b
```

## Support

For issues or IP whitelisting requests, contact: **zeidalqadri**

---

*Powered by Ollama + Qwen3-Coder | Self-hosted, zero cost*
