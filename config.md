# Ollama Chat Service - Configuration

## Server Details

| Item | Value |
|------|-------|
| VPS IP | 45.159.230.42 |
| SSH Port | 1511 |
| SSH Command | `ssh root@45.159.230.42 -p 1511` |

## Services

| Service | Port | URL |
|---------|------|-----|
| Chat UI | 8501 | http://45.159.230.42:8501 |
| Ollama API | 11434 | http://45.159.230.42:11434 (whitelisted IPs only) |
| Chroma DB | 8000 | http://45.159.230.42:8000 |

## Models Installed

- qwen3-coder:30b (18GB) - Primary
- qwen2.5-coder:14b (9GB) - Backup/faster

## File Locations (VPS)

| File | Path |
|------|------|
| Streamlit App | /opt/ollama-ui/app.py |
| User Database | /opt/ollama-ui/users.db |
| Ollama Models | /usr/share/ollama/.ollama/models |
| Chroma Data | /opt/chroma-data |

## Systemd Services

```bash
# Ollama
systemctl status ollama
systemctl restart ollama

# Chat UI
systemctl status ollama-ui
systemctl restart ollama-ui
```

## Firewall Rules

- Port 8501: Open to all (Chat UI)
- Port 11434: Whitelisted IPs only (Ollama API)
- Port 8000: Open to all (Chroma)

## Whitelisted IPs

- 14.192.214.143 (zeidalqadri)
