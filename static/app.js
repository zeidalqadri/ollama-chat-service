/**
 * BORAK - Client-side Application
 * Handles authentication, chat, streaming, and UI state
 */

// =============================================================================
// Base Path Detection (for reverse proxy support)
// =============================================================================

// Detect base path from current URL (e.g., /borak01 from /borak01/)
const BASE_PATH = window.location.pathname.replace(/\/$/, '') || '';
const API_BASE = BASE_PATH + '/api';

// =============================================================================
// State
// =============================================================================

const state = {
    authenticated: false,
    username: null,
    models: [],
    selectedModel: null,
    visionModels: [],
    messages: [],
    uploadedImage: null,
    lastOutput: null,
    isGenerating: false
};

// =============================================================================
// DOM Elements
// =============================================================================

const elements = {
    // Views
    loginView: document.getElementById('login-view'),
    chatView: document.getElementById('chat-view'),

    // Auth
    loginForm: document.getElementById('login-form'),
    registerForm: document.getElementById('register-form'),
    authAlert: document.getElementById('auth-alert'),
    tabBtns: document.querySelectorAll('.tab-btn'),

    // Sidebar
    sidebar: document.getElementById('sidebar'),
    panelToggle: document.getElementById('panel-toggle'),
    displayUsername: document.getElementById('display-username'),
    modelSelect: document.getElementById('model-select'),
    visionBadge: document.getElementById('vision-badge'),
    imageInput: document.getElementById('image-input'),
    fileUpload: document.getElementById('file-upload'),
    imagePreview: document.getElementById('image-preview'),
    previewImg: document.getElementById('preview-img'),
    removeImage: document.getElementById('remove-image'),
    clearChat: document.getElementById('clear-chat'),
    logoutBtn: document.getElementById('logout-btn'),

    // Chat
    messages: document.getElementById('messages'),
    chatInput: document.getElementById('chat-input'),
    sendBtn: document.getElementById('send-btn'),

    // Canvas
    canvasContent: document.getElementById('canvas-content')
};

// =============================================================================
// API Functions
// =============================================================================

async function api(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    });

    if (response.status === 401) {
        showLoginView();
        throw new Error('Unauthorized');
    }

    return response;
}

async function checkAuth() {
    try {
        const response = await api('/auth/me');
        if (response.ok) {
            const data = await response.json();
            state.authenticated = true;
            state.username = data.username;
            return true;
        }
    } catch (e) {
        // Not authenticated
    }
    return false;
}

async function login(username, password) {
    const response = await api('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password })
    });

    if (response.ok) {
        const data = await response.json();
        state.authenticated = true;
        state.username = data.username;
        return { success: true };
    }

    const error = await response.json();
    return { success: false, error: error.detail || 'Login failed' };
}

async function register(username, password) {
    const response = await api('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ username, password })
    });

    if (response.ok) {
        return { success: true };
    }

    const error = await response.json();
    return { success: false, error: error.detail || 'Registration failed' };
}

async function logout() {
    await api('/auth/logout', { method: 'POST' });
    state.authenticated = false;
    state.username = null;
    state.messages = [];
    state.lastOutput = null;
}

async function loadModels() {
    try {
        const response = await api('/models');
        if (response.ok) {
            const data = await response.json();
            state.models = data.models;
            state.visionModels = data.vision_models;
            state.selectedModel = data.default;
            return data.models;
        }
    } catch (e) {
        console.error('Failed to load models:', e);
    }
    return [];
}

async function loadChatHistory() {
    try {
        const response = await api('/chat/history');
        if (response.ok) {
            const data = await response.json();
            state.messages = data.messages || [];
            return state.messages;
        }
    } catch (e) {
        console.error('Failed to load chat history:', e);
    }
    return [];
}

async function clearChatHistory() {
    try {
        await api('/chat/clear', { method: 'DELETE' });
        state.messages = [];
        state.lastOutput = null;
        return true;
    } catch (e) {
        console.error('Failed to clear chat:', e);
        return false;
    }
}

async function sendMessage(message, model, images = null) {
    const payload = { message, model };
    if (images) {
        payload.images = images;
    }

    const response = await fetch(`${API_BASE}/chat/send`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    return response;
}

// =============================================================================
// UI Functions
// =============================================================================

function showLoginView() {
    elements.loginView.style.display = 'flex';
    elements.chatView.classList.remove('active');
}

function showChatView() {
    elements.loginView.style.display = 'none';
    elements.chatView.classList.add('active');
    elements.displayUsername.textContent = `> ${state.username}`;
}

function showAlert(message, type = 'error') {
    elements.authAlert.textContent = message;
    elements.authAlert.className = `alert alert-${type}`;
    elements.authAlert.classList.remove('hidden');
    setTimeout(() => {
        elements.authAlert.classList.add('hidden');
    }, 5000);
}

function populateModels() {
    elements.modelSelect.innerHTML = '';
    state.models.forEach(model => {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        if (model === state.selectedModel) {
            option.selected = true;
        }
        elements.modelSelect.appendChild(option);
    });
    updateVisionBadge();
}

function updateVisionBadge() {
    const isVision = state.visionModels.some(vm =>
        state.selectedModel.toLowerCase().includes(vm)
    );
    elements.visionBadge.classList.toggle('hidden', !isVision);
}

function renderMessages() {
    elements.messages.innerHTML = '';
    state.messages.forEach(msg => {
        addMessageToDOM(msg.role, msg.content, msg.hasImage, msg.model);
    });
    scrollToBottom();
}

function addMessageToDOM(role, content, hasImage = false, modelName = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const roleLabel = document.createElement('div');
    roleLabel.className = 'message-role';
    roleLabel.textContent = role === 'user' ? state.username : (modelName || state.selectedModel);
    messageDiv.appendChild(roleLabel);

    if (hasImage) {
        const imageLabel = document.createElement('div');
        imageLabel.className = 'image-attached';
        imageLabel.textContent = 'IMAGE ATTACHED';
        messageDiv.appendChild(imageLabel);
    }

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = formatContent(content);
    messageDiv.appendChild(contentDiv);

    elements.messages.appendChild(messageDiv);
}

function formatContent(content) {
    if (!content) return '';

    // Escape HTML
    let html = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Code blocks
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang || 'text'}">${code}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    return html;
}

function scrollToBottom() {
    elements.messages.scrollTop = elements.messages.scrollHeight;
}

function setGenerating(isGenerating) {
    state.isGenerating = isGenerating;
    elements.sendBtn.disabled = isGenerating;
    elements.chatInput.disabled = isGenerating;
    if (isGenerating) {
        elements.sidebar.classList.add('disabled');
    } else {
        elements.sidebar.classList.remove('disabled');
    }
}

function updateCanvas() {
    if (!state.lastOutput) {
        elements.canvasContent.innerHTML = `
            <div class="canvas-empty">
                <p class="canvas-empty-text">AWAITING OUTPUT</p>
                <p class="canvas-empty-sub">Code blocks and text will render here</p>
            </div>
        `;
        return;
    }

    const codeBlocks = extractCodeBlocks(state.lastOutput);
    let html = '';

    if (codeBlocks.length > 0) {
        html += '<p class="code-section-label">CODE EXTRACTED</p>';
        codeBlocks.forEach((block, i) => {
            const ext = getFileExtension(block.lang);
            html += `
                <div class="code-block">
                    <div class="code-block-header">
                        <span class="code-block-lang">[${i + 1}] ${block.lang.toUpperCase()}</span>
                        <button class="btn btn-small download-code" data-index="${i}">EXPORT .${ext.toUpperCase()}</button>
                    </div>
                    <div class="code-block-content">
                        <pre><code>${escapeHtml(block.code)}</code></pre>
                    </div>
                </div>
            `;
        });
    } else {
        html += '<p class="code-section-label">TEXT OUTPUT</p>';
        html += `<div class="text-output">${escapeHtml(state.lastOutput)}</div>`;
        html += `<button class="download-btn" id="download-text">EXPORT .TXT</button>`;
    }

    elements.canvasContent.innerHTML = html;

    // Add download handlers
    document.querySelectorAll('.download-code').forEach(btn => {
        btn.addEventListener('click', () => {
            const index = parseInt(btn.dataset.index);
            const block = codeBlocks[index];
            downloadFile(`output_${index + 1}.${getFileExtension(block.lang)}`, block.code);
        });
    });

    const downloadText = document.getElementById('download-text');
    if (downloadText) {
        downloadText.addEventListener('click', () => {
            downloadFile('output.txt', state.lastOutput);
        });
    }
}

function extractCodeBlocks(text) {
    const pattern = /```(\w+)?\n([\s\S]*?)```/g;
    const blocks = [];
    let match;
    while ((match = pattern.exec(text)) !== null) {
        blocks.push({
            lang: match[1] || 'text',
            code: match[2].trim()
        });
    }
    return blocks;
}

function getFileExtension(lang) {
    const map = {
        python: 'py',
        javascript: 'js',
        typescript: 'ts',
        html: 'html',
        css: 'css',
        json: 'json',
        yaml: 'yaml',
        yml: 'yml',
        markdown: 'md',
        java: 'java',
        cpp: 'cpp',
        c: 'c',
        go: 'go',
        rust: 'rs',
        ruby: 'rb',
        php: 'php',
        shell: 'sh',
        bash: 'sh',
        sql: 'sql'
    };
    return map[lang.toLowerCase()] || 'txt';
}

function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function downloadFile(filename, content) {
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// =============================================================================
// Event Handlers
// =============================================================================

// Tab switching
elements.tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        elements.tabBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        if (tab === 'login') {
            elements.loginForm.classList.remove('hidden');
            elements.registerForm.classList.add('hidden');
        } else {
            elements.loginForm.classList.add('hidden');
            elements.registerForm.classList.remove('hidden');
        }
    });
});

// Login form
elements.loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    const result = await login(username, password);
    if (result.success) {
        await initChat();
        showChatView();
    } else {
        showAlert(result.error);
    }
});

// Register form
elements.registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('reg-username').value;
    const password = document.getElementById('reg-password').value;
    const confirm = document.getElementById('reg-confirm').value;

    if (password.length < 6) {
        showAlert('Password must be at least 6 characters');
        return;
    }

    if (password !== confirm) {
        showAlert('Passwords do not match');
        return;
    }

    const result = await register(username, password);
    if (result.success) {
        showAlert('Account created. Login now.', 'success');
        // Switch to login tab
        elements.tabBtns.forEach(b => b.classList.remove('active'));
        elements.tabBtns[0].classList.add('active');
        elements.loginForm.classList.remove('hidden');
        elements.registerForm.classList.add('hidden');
    } else {
        showAlert(result.error);
    }
});

// Panel toggle
elements.panelToggle.addEventListener('click', () => {
    elements.sidebar.classList.toggle('hidden');
    elements.panelToggle.textContent = elements.sidebar.classList.contains('hidden') ? 'PANEL' : 'PANEL';
});

// Model select
elements.modelSelect.addEventListener('change', () => {
    state.selectedModel = elements.modelSelect.value;
    updateVisionBadge();
});

// Image upload
elements.fileUpload.addEventListener('click', () => {
    elements.imageInput.click();
});

elements.imageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
            const base64 = event.target.result.split(',')[1];
            state.uploadedImage = base64;
            elements.previewImg.src = event.target.result;
            elements.imagePreview.classList.remove('hidden');
            elements.fileUpload.classList.add('hidden');
        };
        reader.readAsDataURL(file);
    }
});

elements.removeImage.addEventListener('click', () => {
    state.uploadedImage = null;
    elements.imageInput.value = '';
    elements.imagePreview.classList.add('hidden');
    elements.fileUpload.classList.remove('hidden');
});

// Clear chat
elements.clearChat.addEventListener('click', async () => {
    if (await clearChatHistory()) {
        renderMessages();
        updateCanvas();
    }
});

// Logout
elements.logoutBtn.addEventListener('click', async () => {
    await logout();
    showLoginView();
});

// Send message
elements.sendBtn.addEventListener('click', handleSendMessage);

elements.chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
    }
});

// Auto-resize textarea
elements.chatInput.addEventListener('input', () => {
    elements.chatInput.style.height = 'auto';
    elements.chatInput.style.height = Math.min(elements.chatInput.scrollHeight, 150) + 'px';
});

async function handleSendMessage() {
    const message = elements.chatInput.value.trim();
    if (!message || state.isGenerating) return;

    const hasImage = !!state.uploadedImage;
    const images = hasImage ? [state.uploadedImage] : null;

    // Add user message to state and DOM
    state.messages.push({ role: 'user', content: message, hasImage });
    addMessageToDOM('user', message, hasImage);
    scrollToBottom();

    // Clear input
    elements.chatInput.value = '';
    elements.chatInput.style.height = 'auto';

    // Clear image
    if (state.uploadedImage) {
        state.uploadedImage = null;
        elements.imageInput.value = '';
        elements.imagePreview.classList.add('hidden');
        elements.fileUpload.classList.remove('hidden');
    }

    // Start streaming
    setGenerating(true);

    // Create assistant message placeholder
    const assistantDiv = document.createElement('div');
    assistantDiv.className = 'message assistant';

    const roleDiv = document.createElement('div');
    roleDiv.className = 'message-role';
    roleDiv.textContent = state.selectedModel;
    assistantDiv.appendChild(roleDiv);

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content generating-indicator';
    contentDiv.textContent = 'Generating...';
    assistantDiv.appendChild(contentDiv);

    elements.messages.appendChild(assistantDiv);
    scrollToBottom();

    let fullResponse = '';

    try {
        const response = await sendMessage(message, state.selectedModel, images);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const text = decoder.decode(value);
            const lines = text.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6);
                    if (!jsonStr) continue;

                    try {
                        const data = JSON.parse(jsonStr);

                        if (data.type === 'content') {
                            fullResponse += data.content;
                            contentDiv.innerHTML = formatContent(fullResponse) + '<span class="streaming-cursor">|</span>';
                            scrollToBottom();
                        } else if (data.type === 'done') {
                            contentDiv.innerHTML = formatContent(fullResponse);
                            state.messages.push({ role: 'assistant', content: fullResponse, model: state.selectedModel });
                            state.lastOutput = fullResponse;
                            updateCanvas();
                        } else if (data.type === 'error') {
                            contentDiv.innerHTML = `<em>Error: ${data.error}</em>`;
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Stream error:', error);
        contentDiv.innerHTML = `<em>Error: ${error.message}</em>`;
    }

    setGenerating(false);
}

// =============================================================================
// Initialization
// =============================================================================

async function initChat() {
    await loadModels();
    populateModels();
    await loadChatHistory();
    renderMessages();
    updateCanvas();
}

async function init() {
    const isAuthenticated = await checkAuth();

    if (isAuthenticated) {
        await initChat();
        showChatView();
    } else {
        showLoginView();
    }
}

// Start the app
init();
