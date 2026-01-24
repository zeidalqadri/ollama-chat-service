#!/bin/bash
# Admin scripts for Ollama Chat Service
# VPS: ssh root@45.159.230.42 -p 1511

VPS="root@45.159.230.42"
PORT=1511

# Whitelist an IP for direct Ollama access
whitelist_ip() {
    ssh -p $PORT $VPS "ufw allow from $1 to any port 11434"
    echo "✓ Whitelisted $1"
}

# List all registered users
list_users() {
    ssh -p $PORT $VPS "sqlite3 /opt/ollama-ui/users.db 'SELECT id, username, created_at, last_login FROM users;'"
}

# View usage stats
usage_stats() {
    ssh -p $PORT $VPS "sqlite3 -header -column /opt/ollama-ui/users.db '
        SELECT u.username, 
               COUNT(l.id) as requests,
               SUM(l.tokens_in) as tokens_in, 
               SUM(l.tokens_out) as tokens_out 
        FROM usage_log l 
        JOIN users u ON l.user_id = u.id 
        GROUP BY u.username;'"
}

# Restart services
restart_services() {
    ssh -p $PORT $VPS "systemctl restart ollama ollama-ui"
    echo "✓ Services restarted"
}

# Check service status
status() {
    ssh -p $PORT $VPS "systemctl status ollama ollama-ui --no-pager | grep -E 'Active:|●'"
}

# View logs
logs() {
    ssh -p $PORT $VPS "journalctl -u ollama-ui -n 50 --no-pager"
}

# Pull a new model
pull_model() {
    ssh -p $PORT $VPS "ollama pull $1"
}

# List models
list_models() {
    ssh -p $PORT $VPS "ollama list"
}

# Show help
help() {
    echo "Usage: source admin-scripts.sh"
    echo ""
    echo "Commands:"
    echo "  whitelist_ip <IP>    - Allow IP for direct Ollama access"
    echo "  list_users           - Show registered users"
    echo "  usage_stats          - Show token usage per user"
    echo "  restart_services     - Restart Ollama and UI"
    echo "  status               - Check service status"
    echo "  logs                 - View UI logs"
    echo "  pull_model <name>    - Download a new model"
    echo "  list_models          - Show installed models"
}

echo "Admin scripts loaded. Type 'help' for commands."
