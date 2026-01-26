/**
 * BORAK - Client-side Application
 * Handles authentication, chat, streaming, sessions, and artifacts
 */

// =============================================================================
// Base Path Detection (for reverse proxy support)
// =============================================================================

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
    translationModels: [],
    messages: [],
    uploadedImage: null,
    lastOutput: null,
    isGenerating: false,
    // Session management
    currentSessionId: null,
    sessions: [],
    hasMoreSessions: false,
    sessionsOffset: 0,
    // Generation control
    generationController: null,
    canContinue: false,
    // Artifacts
    artifacts: { code: [], thought: [], explanation: [] },
    selectedArtifact: null,
    // Scroll control - only auto-scroll if user is near bottom
    userScrolledUp: false,
    // Settings
    settings: {
        system_prompt: null,
        system_prompt_enabled: true,
        model_prompts: {}
    },
    presets: []
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
    translationBadge: document.getElementById('translation-badge'),
    imageInput: document.getElementById('image-input'),
    fileUpload: document.getElementById('file-upload'),
    imagePreview: document.getElementById('image-preview'),
    previewImg: document.getElementById('preview-img'),
    removeImage: document.getElementById('remove-image'),
    clearChat: document.getElementById('clear-chat'),
    logoutBtn: document.getElementById('logout-btn'),

    // Sessions
    newChatBtn: document.getElementById('new-chat-btn'),
    sessionList: document.getElementById('session-list'),
    loadMoreSessions: document.getElementById('load-more-sessions'),

    // Chat
    messages: document.getElementById('messages'),
    chatInput: document.getElementById('chat-input'),
    sendBtn: document.getElementById('send-btn'),
    stopBtn: document.getElementById('stop-btn'),
    continueBtn: document.getElementById('continue-btn'),

    // Inline attachment (next to chat input)
    attachBtn: document.getElementById('attach-btn'),
    inlineImageInput: document.getElementById('inline-image-input'),
    inlineImagePreview: document.getElementById('inline-image-preview'),
    inlinePreviewImg: document.getElementById('inline-preview-img'),
    inlineRemoveImage: document.getElementById('inline-remove-image'),

    // Canvas / Artifacts
    canvasContent: document.getElementById('canvas-content'),
    canvasPanel: document.querySelector('.canvas-panel'),
    downloadAllBtn: document.getElementById('download-all-btn'),
    canvasEmpty: document.getElementById('canvas-empty'),
    artifactPreview: document.getElementById('artifact-preview'),
    previewTitle: document.getElementById('preview-title'),
    previewContent: document.getElementById('preview-content'),
    copyArtifact: document.getElementById('copy-artifact'),
    downloadArtifact: document.getElementById('download-artifact'),
    closePreview: document.getElementById('close-preview'),

    // Artifact folders
    codeArtifacts: document.getElementById('code-artifacts'),
    thoughtArtifacts: document.getElementById('thought-artifacts'),
    documentArtifacts: document.getElementById('document-artifacts'),
    codeCount: document.getElementById('code-count'),
    thoughtCount: document.getElementById('thought-count'),
    documentCount: document.getElementById('document-count'),

    // Mobile
    sidebarOverlay: document.getElementById('sidebar-overlay'),

    // Settings modal
    settingsBtn: document.getElementById('settings-btn'),
    settingsModal: document.getElementById('settings-modal'),
    closeSettings: document.getElementById('close-settings'),
    cancelSettings: document.getElementById('cancel-settings'),
    saveSettings: document.getElementById('save-settings'),
    systemPromptEnabled: document.getElementById('system-prompt-enabled'),
    presetSelect: document.getElementById('preset-select'),
    systemPromptInput: document.getElementById('system-prompt-input'),
    promptCharCount: document.getElementById('prompt-char-count')
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
    state.currentSessionId = null;
    state.sessions = [];
}

async function loadModels() {
    try {
        const response = await api('/models');
        if (response.ok) {
            const data = await response.json();
            state.models = data.models;
            state.visionModels = data.vision_models;
            state.translationModels = data.translation_models || [];
            state.selectedModel = data.default;
            return data.models;
        }
    } catch (e) {
        console.error('Failed to load models:', e);
    }
    return [];
}

// =============================================================================
// Session API Functions
// =============================================================================

async function createSession(name = 'New Chat') {
    try {
        const response = await api('/sessions', {
            method: 'POST',
            body: JSON.stringify({ name })
        });
        if (response.ok) {
            const data = await response.json();
            return data.session_id;
        }
    } catch (e) {
        console.error('Failed to create session:', e);
    }
    return null;
}

async function loadSessions(reset = true) {
    try {
        if (reset) {
            state.sessionsOffset = 0;
        }
        const response = await api(`/sessions?limit=20&offset=${state.sessionsOffset}`);
        if (response.ok) {
            const data = await response.json();
            if (reset) {
                state.sessions = data.sessions;
            } else {
                state.sessions = [...state.sessions, ...data.sessions];
            }
            state.hasMoreSessions = data.has_more;
            state.sessionsOffset += data.sessions.length;
            return state.sessions;
        }
    } catch (e) {
        console.error('Failed to load sessions:', e);
    }
    return [];
}

async function renameSession(sessionId, newName) {
    try {
        const response = await api(`/sessions/${sessionId}`, {
            method: 'PATCH',
            body: JSON.stringify({ name: newName })
        });
        return response.ok;
    } catch (e) {
        console.error('Failed to rename session:', e);
    }
    return false;
}

async function deleteSession(sessionId) {
    try {
        const response = await api(`/sessions/${sessionId}`, {
            method: 'DELETE'
        });
        return response.ok;
    } catch (e) {
        console.error('Failed to delete session:', e);
    }
    return false;
}

async function loadChatHistory(sessionId = null) {
    try {
        const url = sessionId ? `/chat/history?session_id=${sessionId}` : '/chat/history';
        const response = await api(url);
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

async function clearChatHistory(sessionId = null) {
    try {
        const url = sessionId ? `/chat/clear?session_id=${sessionId}` : '/chat/clear';
        await api(url, { method: 'DELETE' });
        state.messages = [];
        state.lastOutput = null;
        state.canContinue = false;
        return true;
    } catch (e) {
        console.error('Failed to clear chat:', e);
        return false;
    }
}

// =============================================================================
// Artifact API Functions
// =============================================================================

async function loadArtifacts(sessionId) {
    // Load user-level persistent artifacts (not session-bound)
    try {
        const response = await api('/user/artifacts');
        if (response.ok) {
            const data = await response.json();
            state.artifacts = data;
            return data;
        }
    } catch (e) {
        console.error('Failed to load artifacts:', e);
    }
    return { code: [], thought: [], document: [] };
}

async function deleteArtifact(artifactId) {
    try {
        const response = await api(`/user/artifacts/${artifactId}`, {
            method: 'DELETE'
        });
        return response.ok;
    } catch (e) {
        console.error('Failed to delete artifact:', e);
    }
    return false;
}

async function downloadArtifactsZip(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/sessions/${sessionId}/artifacts/download`, {
            credentials: 'include'
        });
        if (response.ok) {
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `session_${sessionId}_artifacts.zip`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    } catch (e) {
        console.error('Failed to download artifacts:', e);
    }
}

// =============================================================================
// Settings API Functions
// =============================================================================

async function loadSettings() {
    try {
        const response = await api('/user/settings');
        if (response.ok) {
            const data = await response.json();
            state.settings = data;
            return data;
        }
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
    return state.settings;
}

async function saveSettingsToServer(settings) {
    try {
        const response = await api('/user/settings', {
            method: 'PUT',
            body: JSON.stringify(settings)
        });
        if (response.ok) {
            state.settings = settings;
            return true;
        }
    } catch (e) {
        console.error('Failed to save settings:', e);
    }
    return false;
}

async function loadPresets() {
    try {
        const response = await api('/prompts/presets');
        if (response.ok) {
            const data = await response.json();
            state.presets = data.presets;
            return data.presets;
        }
    } catch (e) {
        console.error('Failed to load presets:', e);
    }
    return [];
}

// =============================================================================
// Generation Control Functions
// =============================================================================

async function stopGeneration() {
    if (!state.currentSessionId) return;

    try {
        const response = await api('/chat/stop', {
            method: 'POST',
            body: JSON.stringify({ session_id: state.currentSessionId })
        });
        if (response.ok) {
            const data = await response.json();
            state.canContinue = true;
            return data;
        }
    } catch (e) {
        console.error('Failed to stop generation:', e);
    }
    return null;
}

async function sendMessage(message, model, sessionId = null, images = null) {
    const payload = { message, model, session_id: sessionId };
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

async function continueGeneration() {
    if (!state.currentSessionId || !state.canContinue) return;

    const response = await fetch(`${API_BASE}/chat/continue`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: state.currentSessionId,
            model: state.selectedModel
        })
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
    elements.displayUsername.textContent = state.username;
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
    updateTranslationBadge();
}

function updateVisionBadge() {
    const isVision = state.visionModels.some(vm =>
        state.selectedModel.toLowerCase().includes(vm)
    );
    elements.visionBadge.classList.toggle('hidden', !isVision);
}

function updateTranslationBadge() {
    const isTranslation = state.translationModels.some(tm =>
        state.selectedModel.toLowerCase().includes(tm)
    );
    if (elements.translationBadge) {
        elements.translationBadge.classList.toggle('hidden', !isTranslation);
    }
}

// =============================================================================
// Session UI Functions
// =============================================================================

function renderSessions() {
    elements.sessionList.innerHTML = '';

    state.sessions.forEach(session => {
        const item = document.createElement('div');
        item.className = `session-item ${session.id === state.currentSessionId ? 'active' : ''}`;
        item.dataset.sessionId = session.id;

        const info = document.createElement('div');
        info.className = 'session-info';

        const name = document.createElement('div');
        name.className = 'session-name';
        name.textContent = session.name;

        const preview = document.createElement('div');
        preview.className = 'session-preview';
        preview.textContent = session.preview || 'Empty';

        info.appendChild(name);
        info.appendChild(preview);

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'session-delete';
        deleteBtn.title = 'Delete';
        deleteBtn.textContent = '×';

        item.appendChild(info);
        item.appendChild(deleteBtn);

        // Click to switch session
        info.addEventListener('click', () => {
            switchSession(session.id);
            handleMobileSessionSelect();
        });

        // Double-click to rename
        name.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            startRenameSession(item, session, name);
        });

        // Delete button
        deleteBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (confirm(`Delete "${session.name}"?`)) {
                await handleDeleteSession(session.id);
            }
        });

        elements.sessionList.appendChild(item);
    });

    // Show/hide load more button
    elements.loadMoreSessions.classList.toggle('hidden', !state.hasMoreSessions);
}

function startRenameSession(item, session, nameEl) {
    const currentName = session.name;

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'session-name-input';
    input.value = currentName;

    nameEl.textContent = '';
    nameEl.appendChild(input);
    input.focus();
    input.select();

    const finishRename = async () => {
        const newName = input.value.trim() || currentName;
        if (newName !== currentName) {
            await renameSession(session.id, newName);
            session.name = newName;
        }
        nameEl.textContent = newName;
    };

    input.addEventListener('blur', finishRename);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            input.blur();
        } else if (e.key === 'Escape') {
            input.value = currentName;
            input.blur();
        }
    });
}

async function switchSession(sessionId) {
    if (state.isGenerating) return;

    state.currentSessionId = sessionId;
    state.canContinue = false;

    // Update active state in UI
    document.querySelectorAll('.session-item').forEach(item => {
        item.classList.toggle('active', parseInt(item.dataset.sessionId) === sessionId);
    });

    // Load messages and artifacts for this session
    await loadChatHistory(sessionId);
    await loadArtifacts(sessionId);

    renderMessages();
    renderArtifacts();
    updateCanContinue();
}

async function handleDeleteSession(sessionId) {
    const success = await deleteSession(sessionId);
    if (success) {
        state.sessions = state.sessions.filter(s => s.id !== sessionId);

        // If deleted current session, switch to another
        if (sessionId === state.currentSessionId) {
            if (state.sessions.length > 0) {
                await switchSession(state.sessions[0].id);
            } else {
                // Create a new session
                const newId = await createSession();
                if (newId) {
                    await loadSessions();
                    await switchSession(newId);
                }
            }
        }

        renderSessions();
    }
}

async function handleNewChat() {
    const sessionId = await createSession();
    if (sessionId) {
        await loadSessions();
        await switchSession(sessionId);
        renderSessions();
    }
}

// =============================================================================
// Message Rendering
// =============================================================================

function renderMessages() {
    elements.messages.innerHTML = '';
    state.messages.forEach(msg => {
        addMessageToDOM(msg.role, msg.content, msg.hasImage, msg.model, msg.is_partial, msg.attachments);
    });
    scrollToBottom();
    updateCanContinue();
}

function addMessageToDOM(role, content, hasImage = false, modelName = null, isPartial = false, attachments = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}${isPartial ? ' partial' : ''}`;

    const roleLabel = document.createElement('div');
    roleLabel.className = 'message-role';
    roleLabel.textContent = role === 'user' ? state.username : (modelName || state.selectedModel);
    messageDiv.appendChild(roleLabel);

    // Show attached images (from server attachments or hasImage flag)
    if (attachments && attachments.length > 0) {
        const attachContainer = document.createElement('div');
        attachContainer.className = 'message-attachments';

        attachments.forEach(att => {
            const imgWrapper = document.createElement('div');
            imgWrapper.className = 'attachment-preview';

            const img = document.createElement('img');
            img.src = att.url;
            img.alt = 'Attached image';
            img.loading = 'lazy';
            img.addEventListener('click', () => {
                // Open in new tab for full view / download
                window.open(att.download_url, '_blank');
            });

            imgWrapper.appendChild(img);
            attachContainer.appendChild(imgWrapper);
        });

        messageDiv.appendChild(attachContainer);
    } else if (hasImage) {
        // Fallback for images sent in current session (not yet persisted or expired)
        const imageLabel = document.createElement('div');
        imageLabel.className = 'image-attached';
        imageLabel.textContent = 'Image attached (processing)';
        messageDiv.appendChild(imageLabel);
    }

    // Bubble wrapper for cleaner design
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    // Content is sanitized via formatContent which escapes HTML first
    contentDiv.innerHTML = formatContent(content);
    bubbleDiv.appendChild(contentDiv);

    messageDiv.appendChild(bubbleDiv);
    elements.messages.appendChild(messageDiv);

    // Apply syntax highlighting
    messageDiv.querySelectorAll('pre code').forEach(el => {
        if (typeof hljs !== 'undefined') {
            hljs.highlightElement(el);
        }
    });
}

function formatContent(content) {
    if (!content) return '';

    // First escape all HTML to prevent XSS
    let html = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Code blocks (safe since content is already escaped)
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang || 'text'}">${code}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Links (href is escaped via the initial escaping)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    return html;
}

function scrollToBottom(force = false) {
    // Only auto-scroll if user hasn't scrolled up (or force is true)
    if (force || !state.userScrolledUp) {
        elements.messages.scrollTop = elements.messages.scrollHeight;
    }
}

function isNearBottom() {
    const threshold = 100; // pixels from bottom
    const { scrollTop, scrollHeight, clientHeight } = elements.messages;
    return scrollHeight - scrollTop - clientHeight < threshold;
}

// Detect user scroll to allow reading while streaming
elements.messages.addEventListener('scroll', () => {
    if (state.isGenerating) {
        state.userScrolledUp = !isNearBottom();
    }
});

function updateCanContinue() {
    // Check if last message is partial
    if (state.messages.length > 0) {
        const lastMsg = state.messages[state.messages.length - 1];
        state.canContinue = lastMsg.role === 'assistant' && lastMsg.is_partial;
    } else {
        state.canContinue = false;
    }
    elements.continueBtn.classList.toggle('hidden', !state.canContinue || state.isGenerating);
}

function setGenerating(isGenerating) {
    state.isGenerating = isGenerating;
    elements.sendBtn.disabled = isGenerating;
    elements.chatInput.disabled = isGenerating;
    elements.stopBtn.classList.toggle('hidden', !isGenerating);
    elements.continueBtn.classList.toggle('hidden', isGenerating || !state.canContinue);

    if (isGenerating) {
        elements.sidebar.classList.add('disabled');
    } else {
        elements.sidebar.classList.remove('disabled');
        // Reset scroll tracking when generation ends
        state.userScrolledUp = false;
    }
}

// =============================================================================
// Artifact Rendering
// =============================================================================

function renderArtifacts() {
    const { code, thought, document: docs } = state.artifacts;
    const codeItems = code || [];
    const thoughtItems = thought || [];
    const docItems = docs || [];

    // Update counts
    elements.codeCount.textContent = `(${codeItems.length})`;
    elements.thoughtCount.textContent = `(${thoughtItems.length})`;
    elements.documentCount.textContent = `(${docItems.length})`;

    // Render items
    renderArtifactItems(elements.codeArtifacts, codeItems, 'code');
    renderArtifactItems(elements.thoughtArtifacts, thoughtItems, 'thought');
    renderArtifactItems(elements.documentArtifacts, docItems, 'document');

    // Show/hide empty state
    const hasArtifacts = codeItems.length + thoughtItems.length + docItems.length > 0;
    elements.canvasEmpty.classList.toggle('hidden', hasArtifacts);
    elements.downloadAllBtn.classList.toggle('hidden', !hasArtifacts);
}

function renderArtifactItems(container, items, type) {
    // Clear container safely
    while (container.firstChild) {
        container.removeChild(container.firstChild);
    }

    items.forEach((item, index) => {
        const el = document.createElement('div');
        el.className = 'artifact-item';
        el.dataset.artifactId = item.id;

        const info = document.createElement('div');
        info.className = 'artifact-info';

        const title = document.createElement('span');
        title.className = 'artifact-title';
        title.textContent = item.title || `${type} ${index + 1}`;
        info.appendChild(title);

        if (item.language) {
            const lang = document.createElement('span');
            lang.className = 'artifact-lang';
            lang.textContent = item.language.toUpperCase();
            info.appendChild(lang);
        }

        el.appendChild(info);

        // Delete button
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'artifact-delete';
        deleteBtn.textContent = '×';
        deleteBtn.title = 'Delete';
        deleteBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (confirm(`Delete "${item.title || type}"?`)) {
                const deleted = await deleteArtifact(item.id);
                if (deleted) {
                    // Remove from state and re-render
                    state.artifacts[type] = state.artifacts[type].filter(a => a.id !== item.id);
                    renderArtifacts();
                    // Close preview if this was selected
                    if (state.selectedArtifact?.id === item.id) {
                        elements.artifactPreview.classList.add('hidden');
                        state.selectedArtifact = null;
                    }
                }
            }
        });
        el.appendChild(deleteBtn);

        info.addEventListener('click', () => {
            selectArtifact(item, type);
        });

        container.appendChild(el);
    });
}

function selectArtifact(artifact, type) {
    state.selectedArtifact = { ...artifact, type };

    // Update active state
    document.querySelectorAll('.artifact-item').forEach(item => {
        item.classList.toggle('active', parseInt(item.dataset.artifactId) === artifact.id);
    });

    // Show preview
    elements.artifactPreview.classList.remove('hidden');
    elements.previewTitle.textContent = artifact.title || 'Artifact';

    // Build preview content safely
    const pre = document.createElement('pre');
    if (type === 'code' && artifact.language) {
        const code = document.createElement('code');
        code.className = `language-${artifact.language}`;
        code.textContent = artifact.content;
        pre.appendChild(code);
        if (typeof hljs !== 'undefined') {
            hljs.highlightElement(code);
        }
    } else {
        pre.textContent = artifact.content;
    }

    elements.previewContent.innerHTML = '';
    elements.previewContent.appendChild(pre);
}

function extractArtifactsRealtime(content) {
    // Extract counts for real-time display during streaming
    const codeCount = (content.match(/```(\w+)?\n[\s\S]*?```/g) || []).length;
    const thoughtCount = (content.match(/&lt;think&gt;[\s\S]*?&lt;\/think&gt;/g) || []).length;
    const sectionCount = (content.match(/^##\s+.+?\n[\s\S]{50,}?(?=^##|\Z)/gm) || []).length;

    // Add to existing counts from user artifacts
    const existingCode = (state.artifacts.code || []).length;
    const existingThought = (state.artifacts.thought || []).length;
    const existingDocs = (state.artifacts.document || []).length;

    elements.codeCount.textContent = `(${existingCode + codeCount})`;
    elements.thoughtCount.textContent = `(${existingThought + thoughtCount})`;
    elements.documentCount.textContent = `(${existingDocs + sectionCount})`;
}

// =============================================================================
// Helper Functions
// =============================================================================

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function getFileExtension(lang) {
    const map = {
        python: 'py', javascript: 'js', typescript: 'ts',
        html: 'html', css: 'css', json: 'json', yaml: 'yaml', yml: 'yml',
        markdown: 'md', java: 'java', cpp: 'cpp', c: 'c',
        go: 'go', rust: 'rs', ruby: 'rb', php: 'php',
        shell: 'sh', bash: 'sh', sql: 'sql'
    };
    return map[(lang || '').toLowerCase()] || 'txt';
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

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Optional: show feedback
    }).catch(err => {
        console.error('Failed to copy:', err);
    });
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
    const isVisible = elements.sidebar.classList.contains('visible');
    if (isVisible) {
        closeSidebar();
    } else {
        openSidebar();
    }
});

// Sidebar overlay click (mobile)
if (elements.sidebarOverlay) {
    elements.sidebarOverlay.addEventListener('click', closeSidebar);
}

// Canvas panel toggle (mobile)
const canvasHeader = document.querySelector('.canvas-header');
if (canvasHeader) {
    canvasHeader.addEventListener('click', (e) => {
        // Only toggle on mobile
        if (window.innerWidth <= 768) {
            elements.canvasPanel.classList.toggle('expanded');
        }
    });
}

function openSidebar() {
    elements.sidebar.classList.remove('hidden');
    elements.sidebar.classList.add('visible');
    if (elements.sidebarOverlay) {
        elements.sidebarOverlay.classList.add('active');
    }
    document.body.style.overflow = 'hidden';
}

function closeSidebar() {
    elements.sidebar.classList.add('hidden');
    elements.sidebar.classList.remove('visible');
    if (elements.sidebarOverlay) {
        elements.sidebarOverlay.classList.remove('active');
    }
    document.body.style.overflow = '';
}

// Close sidebar when selecting a session on mobile
function handleMobileSessionSelect() {
    if (window.innerWidth <= 768) {
        closeSidebar();
    }
}

// Model select
elements.modelSelect.addEventListener('change', () => {
    state.selectedModel = elements.modelSelect.value;
    updateVisionBadge();
    updateTranslationBadge();
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
            // Also update inline preview
            if (elements.inlinePreviewImg) {
                elements.inlinePreviewImg.src = event.target.result;
                elements.inlineImagePreview.classList.remove('hidden');
            }
            if (elements.attachBtn) {
                elements.attachBtn.classList.add('has-image');
            }
        };
        reader.readAsDataURL(file);
    }
});

elements.removeImage.addEventListener('click', () => {
    clearUploadedImage();
});

// Inline image upload (next to chat input)
if (elements.attachBtn) {
    elements.attachBtn.addEventListener('click', () => {
        elements.inlineImageInput.click();
    });
}

if (elements.inlineImageInput) {
    elements.inlineImageInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                const base64 = event.target.result.split(',')[1];
                state.uploadedImage = base64;
                // Update both previews for consistency
                if (elements.inlinePreviewImg) {
                    elements.inlinePreviewImg.src = event.target.result;
                    elements.inlineImagePreview.classList.remove('hidden');
                }
                if (elements.attachBtn) {
                    elements.attachBtn.classList.add('has-image');
                }
                // Also update sidebar preview if it exists
                if (elements.previewImg) {
                    elements.previewImg.src = event.target.result;
                    elements.imagePreview.classList.remove('hidden');
                    elements.fileUpload.classList.add('hidden');
                }
            };
            reader.readAsDataURL(file);
        }
    });
}

if (elements.inlineRemoveImage) {
    elements.inlineRemoveImage.addEventListener('click', () => {
        clearUploadedImage();
    });
}

// Helper to clear uploaded image from all locations
function clearUploadedImage() {
    state.uploadedImage = null;
    // Clear sidebar upload
    if (elements.imageInput) elements.imageInput.value = '';
    if (elements.imagePreview) elements.imagePreview.classList.add('hidden');
    if (elements.fileUpload) elements.fileUpload.classList.remove('hidden');
    // Clear inline upload
    if (elements.inlineImageInput) elements.inlineImageInput.value = '';
    if (elements.inlineImagePreview) elements.inlineImagePreview.classList.add('hidden');
    if (elements.attachBtn) elements.attachBtn.classList.remove('has-image');
}

// Session controls
elements.newChatBtn.addEventListener('click', handleNewChat);

elements.loadMoreSessions.addEventListener('click', async () => {
    await loadSessions(false);
    renderSessions();
});

// Clear chat
elements.clearChat.addEventListener('click', async () => {
    if (await clearChatHistory(state.currentSessionId)) {
        state.artifacts = { code: [], thought: [], explanation: [] };
        renderMessages();
        renderArtifacts();
    }
});

// Logout
elements.logoutBtn.addEventListener('click', async () => {
    await logout();
    showLoginView();
});

// =============================================================================
// Settings Modal Handlers
// =============================================================================

function openSettingsModal() {
    // Load current settings into the form
    elements.systemPromptEnabled.checked = state.settings.system_prompt_enabled;
    elements.systemPromptInput.value = state.settings.system_prompt || '';
    updateCharCount();

    // Populate presets dropdown
    populatePresets();

    // Show modal
    elements.settingsModal.classList.remove('hidden');
}

function closeSettingsModal() {
    elements.settingsModal.classList.add('hidden');
}

function populatePresets() {
    // Clear existing options safely
    while (elements.presetSelect.firstChild) {
        elements.presetSelect.removeChild(elements.presetSelect.firstChild);
    }

    state.presets.forEach(preset => {
        const option = document.createElement('option');
        option.value = preset.id;
        option.textContent = preset.name;
        elements.presetSelect.appendChild(option);
    });

    // Select current preset if it matches
    const currentPrompt = state.settings.system_prompt;
    const matchingPreset = state.presets.find(p => p.prompt === currentPrompt);
    if (matchingPreset) {
        elements.presetSelect.value = matchingPreset.id;
    } else if (currentPrompt) {
        // Custom prompt, don't select any preset
        elements.presetSelect.value = 'none';
    }
}

function updateCharCount() {
    const count = elements.systemPromptInput.value.length;
    elements.promptCharCount.textContent = count;
}

// Settings button click
if (elements.settingsBtn) {
    elements.settingsBtn.addEventListener('click', openSettingsModal);
}

// Close settings modal
if (elements.closeSettings) {
    elements.closeSettings.addEventListener('click', closeSettingsModal);
}

if (elements.cancelSettings) {
    elements.cancelSettings.addEventListener('click', closeSettingsModal);
}

// Click outside modal to close
if (elements.settingsModal) {
    elements.settingsModal.querySelector('.modal-backdrop').addEventListener('click', closeSettingsModal);
}

// Preset selection
if (elements.presetSelect) {
    elements.presetSelect.addEventListener('change', () => {
        const presetId = elements.presetSelect.value;
        const preset = state.presets.find(p => p.id === presetId);
        if (preset) {
            elements.systemPromptInput.value = preset.prompt || '';
            updateCharCount();
        }
    });
}

// Character counter
if (elements.systemPromptInput) {
    elements.systemPromptInput.addEventListener('input', updateCharCount);
}

// Save settings
if (elements.saveSettings) {
    elements.saveSettings.addEventListener('click', async () => {
        const settings = {
            system_prompt: elements.systemPromptInput.value.trim() || null,
            system_prompt_enabled: elements.systemPromptEnabled.checked,
            model_prompts: state.settings.model_prompts || {}
        };

        const success = await saveSettingsToServer(settings);
        if (success) {
            closeSettingsModal();
        } else {
            alert('Failed to save settings');
        }
    });
}

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

// Stop button
elements.stopBtn.addEventListener('click', async () => {
    await stopGeneration();
});

// Continue button
elements.continueBtn.addEventListener('click', handleContinue);

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // ESC to stop generation
    if (e.key === 'Escape' && state.isGenerating) {
        stopGeneration();
    }
    // Ctrl+Enter to continue
    if (e.ctrlKey && e.key === 'Enter' && state.canContinue && !state.isGenerating) {
        handleContinue();
    }
});

// Artifact folder toggle
document.querySelectorAll('.folder-header').forEach(header => {
    header.addEventListener('click', () => {
        const folder = header.parentElement;
        folder.classList.toggle('expanded');
        const content = folder.querySelector('.folder-content');
        content.classList.toggle('hidden');
    });
});

// Artifact preview controls
elements.copyArtifact.addEventListener('click', () => {
    if (state.selectedArtifact) {
        copyToClipboard(state.selectedArtifact.content);
    }
});

elements.downloadArtifact.addEventListener('click', () => {
    if (state.selectedArtifact) {
        const ext = getFileExtension(state.selectedArtifact.language);
        const filename = `${state.selectedArtifact.title || 'artifact'}.${ext}`;
        downloadFile(filename, state.selectedArtifact.content);
    }
});

elements.closePreview.addEventListener('click', () => {
    elements.artifactPreview.classList.add('hidden');
    state.selectedArtifact = null;
    document.querySelectorAll('.artifact-item').forEach(item => {
        item.classList.remove('active');
    });
});

// Download all artifacts
elements.downloadAllBtn.addEventListener('click', () => {
    if (state.currentSessionId) {
        downloadArtifactsZip(state.currentSessionId);
    }
});

// Mobile canvas panel toggle
if (elements.canvasPanel) {
    elements.canvasPanel.querySelector('.canvas-header').addEventListener('click', () => {
        if (window.innerWidth <= 768) {
            elements.canvasPanel.classList.toggle('expanded');
        }
    });
}

// =============================================================================
// Message Handling
// =============================================================================

async function handleSendMessage() {
    const message = elements.chatInput.value.trim();
    if (!message || state.isGenerating) return;

    const hasImage = !!state.uploadedImage;
    const images = hasImage ? [state.uploadedImage] : null;

    // Add user message to state and DOM
    state.messages.push({ role: 'user', content: message, hasImage });
    addMessageToDOM('user', message, hasImage);
    state.userScrolledUp = false; // Reset on new message
    scrollToBottom(true); // Force scroll for user's own message

    // Clear input
    elements.chatInput.value = '';
    elements.chatInput.style.height = 'auto';

    // Clear image (use helper to clear all previews)
    if (hasImage) {
        clearUploadedImage();
    }

    // Start streaming
    setGenerating(true);
    state.canContinue = false;

    // Create assistant message placeholder
    const assistantDiv = document.createElement('div');
    assistantDiv.className = 'message assistant';

    const roleDiv = document.createElement('div');
    roleDiv.className = 'message-role';
    roleDiv.textContent = state.selectedModel;
    assistantDiv.appendChild(roleDiv);

    // Bubble wrapper
    const bubbleDiv = document.createElement('div');
    bubbleDiv.className = 'message-bubble';

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content generating-indicator';
    contentDiv.textContent = 'Generating...';
    bubbleDiv.appendChild(contentDiv);

    assistantDiv.appendChild(bubbleDiv);
    elements.messages.appendChild(assistantDiv);
    scrollToBottom();

    let fullResponse = '';

    try {
        const response = await sendMessage(message, state.selectedModel, state.currentSessionId, images);

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

                        if (data.type === 'session') {
                            // Update session ID if auto-created
                            if (!state.currentSessionId) {
                                state.currentSessionId = data.session_id;
                                await loadSessions();
                                renderSessions();
                            }
                        } else if (data.type === 'content') {
                            fullResponse += data.content;
                            // Safe: formatContent escapes HTML first
                            contentDiv.innerHTML = formatContent(fullResponse) + '<span class="streaming-cursor">|</span>';
                            scrollToBottom();

                            // Update artifact counts in real-time
                            extractArtifactsRealtime(fullResponse);
                        } else if (data.type === 'done') {
                            contentDiv.innerHTML = formatContent(fullResponse);
                            contentDiv.querySelectorAll('pre code').forEach(el => {
                                if (typeof hljs !== 'undefined') {
                                    hljs.highlightElement(el);
                                }
                            });
                            state.messages.push({
                                role: 'assistant',
                                content: fullResponse,
                                model: state.selectedModel,
                                is_partial: false
                            });
                            state.lastOutput = fullResponse;

                            // Reload artifacts
                            if (state.currentSessionId) {
                                await loadArtifacts(state.currentSessionId);
                                renderArtifacts();
                            }
                        } else if (data.type === 'stopped') {
                            assistantDiv.classList.add('partial');
                            contentDiv.innerHTML = formatContent(fullResponse);
                            state.messages.push({
                                role: 'assistant',
                                content: fullResponse,
                                model: state.selectedModel,
                                is_partial: true
                            });
                            state.canContinue = true;
                        } else if (data.type === 'error') {
                            const errorMsg = document.createElement('em');
                            errorMsg.textContent = `Error: ${data.error}`;
                            contentDiv.innerHTML = '';
                            contentDiv.appendChild(errorMsg);
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Stream error:', error);
        const errorMsg = document.createElement('em');
        errorMsg.textContent = `Error: ${error.message}`;
        contentDiv.innerHTML = '';
        contentDiv.appendChild(errorMsg);
    }

    setGenerating(false);
    updateCanContinue();
}

async function handleContinue() {
    if (!state.canContinue || state.isGenerating) return;

    setGenerating(true);

    // Get the last assistant message element
    const lastMessageEl = elements.messages.querySelector('.message.assistant:last-child');
    const contentDiv = lastMessageEl?.querySelector('.message-content');

    if (lastMessageEl) {
        lastMessageEl.classList.remove('partial');
        if (contentDiv) {
            const cursor = document.createElement('span');
            cursor.className = 'streaming-cursor';
            cursor.textContent = '|';
            contentDiv.appendChild(cursor);
        }
    }

    let fullResponse = state.messages[state.messages.length - 1]?.content || '';

    try {
        const response = await continueGeneration();

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
                            if (contentDiv) {
                                contentDiv.innerHTML = formatContent(fullResponse) + '<span class="streaming-cursor">|</span>';
                            }
                            scrollToBottom();
                            extractArtifactsRealtime(fullResponse);
                        } else if (data.type === 'done') {
                            if (contentDiv) {
                                contentDiv.innerHTML = formatContent(fullResponse);
                                contentDiv.querySelectorAll('pre code').forEach(el => {
                                    if (typeof hljs !== 'undefined') {
                                        hljs.highlightElement(el);
                                    }
                                });
                            }
                            // Update the message in state
                            if (state.messages.length > 0) {
                                state.messages[state.messages.length - 1].content = fullResponse;
                                state.messages[state.messages.length - 1].is_partial = false;
                            }
                            state.lastOutput = fullResponse;
                            state.canContinue = false;

                            // Reload artifacts
                            if (state.currentSessionId) {
                                await loadArtifacts(state.currentSessionId);
                                renderArtifacts();
                            }
                        } else if (data.type === 'stopped') {
                            if (lastMessageEl) {
                                lastMessageEl.classList.add('partial');
                            }
                            if (contentDiv) {
                                contentDiv.innerHTML = formatContent(fullResponse);
                            }
                            if (state.messages.length > 0) {
                                state.messages[state.messages.length - 1].content = fullResponse;
                                state.messages[state.messages.length - 1].is_partial = true;
                            }
                            state.canContinue = true;
                        } else if (data.type === 'error') {
                            if (contentDiv) {
                                const errorMsg = document.createElement('em');
                                errorMsg.textContent = `Error: ${data.error}`;
                                contentDiv.appendChild(document.createElement('br'));
                                contentDiv.appendChild(errorMsg);
                            }
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Continue error:', error);
        if (contentDiv) {
            const errorMsg = document.createElement('em');
            errorMsg.textContent = `Error: ${error.message}`;
            contentDiv.appendChild(document.createElement('br'));
            contentDiv.appendChild(errorMsg);
        }
    }

    setGenerating(false);
    updateCanContinue();
}

// =============================================================================
// Initialization
// =============================================================================

async function initChat() {
    await loadModels();
    populateModels();

    // Load settings and presets
    await loadSettings();
    await loadPresets();

    // Load sessions
    await loadSessions();

    // Select or create initial session
    if (state.sessions.length > 0) {
        state.currentSessionId = state.sessions[0].id;
    } else {
        const sessionId = await createSession();
        if (sessionId) {
            state.currentSessionId = sessionId;
            await loadSessions();
        }
    }

    renderSessions();

    // Load chat history and artifacts for current session
    if (state.currentSessionId) {
        await loadChatHistory(state.currentSessionId);
        await loadArtifacts(state.currentSessionId);
    }

    renderMessages();
    renderArtifacts();
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
