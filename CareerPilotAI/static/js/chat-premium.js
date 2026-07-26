/**
 * CareerPilot AI — Premium Chat JavaScript
 * Handles real-time chat, Markdown, streaming, shortcuts, and sidebar actions.
 */

// Initialize Marked.js with Highlight.js
if (typeof marked !== 'undefined' && typeof hljs !== 'undefined') {
    const renderer = new marked.Renderer();
    renderer.code = function(code, language) {
        const validLang = hljs.getLanguage(language) ? language : 'plaintext';
        const highlighted = hljs.highlight(code, { language: validLang }).value;
        return `
<div class="code-block-wrapper">
    <div class="code-block-header">
        <span class="code-block-lang">${validLang}</span>
        <button class="code-copy-btn" type="button" onclick="copyCode(this)"><i data-lucide="copy" style="width:14px;height:14px"></i> Copy</button>
    </div>
    <pre><code class="hljs ${validLang}">${highlighted}</code></pre>
</div>`;
    };

    marked.setOptions({
        renderer: renderer,
        breaks: true,
        gfm: true
    });
}

window.copyCode = function(btn) {
    const codeBlock = btn.closest('.code-block-wrapper').querySelector('code');
    navigator.clipboard.writeText(codeBlock.innerText).then(() => {
        const originalHtml = btn.innerHTML;
        btn.innerHTML = `<i data-lucide="check" style="width:14px;height:14px;color:var(--success)"></i> Copied`;
        if (typeof lucide !== 'undefined') lucide.createIcons();
        setTimeout(() => {
            btn.innerHTML = originalHtml;
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }, 2000);
    });
};

const chatForm = document.getElementById('chatForm');
const chatInput = document.getElementById('chatInput');
const chatMessages = document.getElementById('chatMessages');
const sessionId = document.getElementById('sessionId').value;
const sendBtn = document.getElementById('sendBtn');
const charCounter = document.getElementById('charCounter');

// Auto-expand Textarea & Character Count
chatInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    
    const count = this.value.length;
    if (charCounter) {
        charCounter.innerText = `${count} / 5000`;
        if(count > 5000) {
            charCounter.style.color = 'var(--danger)';
            sendBtn.disabled = true;
        } else {
            charCounter.style.color = 'var(--text-tertiary)';
            sendBtn.disabled = count === 0;
        }
    } else {
        sendBtn.disabled = count === 0 || count > 5000;
    }
});

// Submit on Enter, Newline on Shift+Enter
chatInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (this.value.trim() !== '' && this.value.length <= 5000) {
            chatForm.dispatchEvent(new Event('submit'));
        }
    }
});

// Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl + N : New Chat
    if (e.ctrlKey && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        startNewChat();
    }
    // Ctrl + F : Search
    if (e.ctrlKey && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        document.getElementById('chatSearch').focus();
    }
});

function startNewChat() {
    window.location.href = '/chat';
}

function setPrompt(text) {
    chatInput.value = text;
    chatInput.dispatchEvent(new Event('input')); // trigger height/counter update
    chatInput.focus();
    chatForm.requestSubmit();
}

// ── Search & Filter Sidebar ──────────────────────────────────────────
const searchInput = document.getElementById('chatSearch');
if (searchInput) {
    searchInput.addEventListener('input', function(e) {
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.session-card').forEach(item => {
            const title = item.getAttribute('data-title').toLowerCase();
            if (title.includes(term)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

// ── Rename Session ──────────────────────────────────────────────────
function startRename(sid) {
    const item = document.querySelector(`.session-card[data-session-id="${sid}"]`);
    if(!item) return;
    
    // Close dropdown
    const dropdown = document.getElementById(`menu-${sid}`);
    if (dropdown) dropdown.classList.remove('show');
    
    const titleSpan = item.querySelector('.session-title');
    // Remove pin icon text if present
    const pinIcon = titleSpan.querySelector('.pin-icon');
    const oldTitle = pinIcon ? titleSpan.innerText.trim().replace(/^/, '') : titleSpan.innerText.trim();
    
    // Create input
    const input = document.createElement('input');
    input.type = 'text';
    input.value = oldTitle;
    input.style.width = '100%';
    input.style.background = 'var(--bg-primary)';
    input.style.color = 'var(--text-primary)';
    input.style.border = '1px solid var(--primary)';
    input.style.borderRadius = '4px';
    input.style.padding = '2px 4px';
    input.style.fontSize = '0.9rem';
    
    // Temporarily hide original content and show input
    const originalContent = titleSpan.innerHTML;
    titleSpan.innerHTML = '';
    titleSpan.appendChild(input);
    input.focus();
    
    const finalize = () => finishRename(sid, input, oldTitle, originalContent, titleSpan);
    input.addEventListener('blur', finalize);
    input.addEventListener('keydown', (e) => {
        if(e.key === 'Enter') finalize();
        if(e.key === 'Escape') {
            titleSpan.innerHTML = originalContent;
        }
    });
}

function finishRename(sid, input, oldTitle, originalContent, titleSpan) {
    const newTitle = input.value.trim() || oldTitle;
    
    if (newTitle !== oldTitle) {
        titleSpan.innerHTML = originalContent.replace(oldTitle, newTitle);
        // API call
        fetch(`/chat/session/${sid}/rename`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title: newTitle})
        }).then(res => res.json()).then(data => {
            if(data.success) {
                const item = document.querySelector(`.session-card[data-session-id="${sid}"]`);
                if (item) item.setAttribute('data-title', newTitle);
            }
        });
    } else {
        titleSpan.innerHTML = originalContent;
    }
}

// ── Pin Session ─────────────────────────────────────────────────────
function togglePin(sid, isPinned) {
    fetch(`/chat/session/${sid}/pin`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({is_pinned: isPinned})
    }).then(res => res.json()).then(data => {
        if(data.success) {
            window.location.reload();
        }
    });
}

// ── Delete Session ────────────────────────────────────────────────
let pendingDeleteSid = null;

const EMPTY_STATE_HTML = `
    <div class="chat-empty-state">
        <div class="empty-icon-wrapper">
            <i data-lucide="sparkles" style="width:32px;height:32px;color:var(--primary);"></i>
        </div>
        <h2>How can I help you today?</h2>
        <p class="empty-subtitle">I'm your AI Career Coach. Ask me anything about your career.</p>
        
        <div class="empty-suggestions">
            <div class="suggestion-card" onclick="setPrompt('Can you review my resume for a Senior Software Engineer role?')">
                <div class="sugg-icon"><i data-lucide="file-text"></i></div>
                <div class="sugg-text">Review my resume</div>
            </div>
            <div class="suggestion-card" onclick="setPrompt('Let\\'s do a mock interview for a Product Manager position.')">
                <div class="sugg-icon"><i data-lucide="mic"></i></div>
                <div class="sugg-text">Mock interview</div>
            </div>
            <div class="suggestion-card" onclick="setPrompt('What is the best way to negotiate a 20% salary increase?')">
                <div class="sugg-icon"><i data-lucide="dollar-sign"></i></div>
                <div class="sugg-text">Salary negotiation</div>
            </div>
            <div class="suggestion-card" onclick="setPrompt('Create a 3-month learning roadmap to transition to AI Engineering.')">
                <div class="sugg-icon"><i data-lucide="map"></i></div>
                <div class="sugg-text">Learning roadmap</div>
            </div>
        </div>
    </div>
`;

function showWelcomeScreen() {
    chatMessages.innerHTML = EMPTY_STATE_HTML;
    lucide.createIcons();
    document.getElementById('sessionId').value = 'new'; // So that next send creates a new session
    history.pushState(null, '', '/chat/');
}

async function loadSession(sid) {
    document.getElementById('sessionId').value = sid;
    history.pushState(null, '', `/chat/?session_id=${sid}`);
    
    // Update sidebar active class
    document.querySelectorAll('.session-card').forEach(c => c.classList.remove('active'));
    const newActive = document.querySelector(`.session-card[data-session-id="${sid}"]`);
    if (newActive) newActive.classList.add('active');
    
    try {
        const res = await fetch(`/chat/session/${sid}`);
        const data = await res.json();
        
        chatMessages.innerHTML = '';
        if (data.messages && data.messages.length > 0) {
            chatMessages.innerHTML = '<div class="chat-message-row text-center mt-3 mb-4"><span class="chat-date-badge">Today</span></div>';
            data.messages.forEach(msg => {
                appendMessage(msg.role, msg.message, true);
            });
        } else {
            showWelcomeScreen();
        }
        scrollToBottom();
    } catch (e) {
        console.error("Failed to load session", e);
    }
}

function confirmDelete(sid) {
    console.log("Delete clicked");
    console.log("Session ID received:", sid);
    pendingDeleteSid = sid;
    // Close dropdown
    const dropdown = document.getElementById(`menu-${sid}`);
    if (dropdown) dropdown.classList.remove('show');
    document.getElementById('deleteModal').style.display = 'flex';
}
function closeDeleteModal() {
    document.getElementById('deleteModal').style.display = 'none';
    pendingDeleteSid = null;
}

document.getElementById('confirmDeleteBtn').addEventListener('click', async () => {
    const sid = pendingDeleteSid;
    closeDeleteModal();
    if (!sid) return;
    
    console.log("Calling deleteConversation() / fetch API for:", sid);
    
    // Disable button to prevent double click
    const btn = document.getElementById('confirmDeleteBtn');
    const originalText = btn.innerText;
    btn.innerText = 'Deleting...';
    btn.disabled = true;
    
    try {
        const res = await fetch(`/chat/session/${sid}/delete`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        const data = await res.json();
        console.log("Backend response:", data);
        
        if (data.success) {
            const item = document.querySelector(`.session-card[data-session-id="${sid}"]`);
            const allSessions = Array.from(document.querySelectorAll('.session-card'));
            
            let nextId = null;
            if (item) {
                const currentIndex = allSessions.indexOf(item);
                if (currentIndex !== -1) {
                    // Try next, then previous
                    if (currentIndex + 1 < allSessions.length) {
                        nextId = allSessions[currentIndex + 1].getAttribute('data-session-id');
                    } else if (currentIndex - 1 >= 0) {
                        nextId = allSessions[currentIndex - 1].getAttribute('data-session-id');
                    }
                }
                item.remove();
                console.log("Removed sidebar item successfully. Next ID is:", nextId);
            }
            
            // Check if we deleted the active session
            const currentSid = document.getElementById('sessionId').value;
            if (currentSid === sid) {
                if (nextId) {
                    console.log("Loading next conversation dynamically:", nextId);
                    loadSession(nextId);
                } else {
                    console.log("No conversations left, showing Welcome Screen");
                    showWelcomeScreen();
                }
            }
        } else {
            console.error("Delete failed on backend:", data.error);
            showToast("Unable to delete conversation: " + (data.error || "Unknown error"));
        }
    } catch (err) {
        console.error("Failed to delete session due to network error", err);
        showToast("Unable to delete conversation. Network error.");
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
});

function showToast(message) {
    // Check if toast container exists
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.position = 'fixed';
        container.style.bottom = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = 'toast show bg-danger text-white p-3 mb-2 rounded shadow';
    toast.style.minWidth = '250px';
    toast.innerText = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}


// ── Toolbar Actions ─────────────────────────────────────────────────
function copyMessage(btn) {
    const contentDiv = btn.closest('.chat-content').querySelector('.chat-bubble');
    const text = contentDiv.innerText;
    navigator.clipboard.writeText(text);
    
    const icon = btn.innerHTML;
    btn.innerHTML = '<i data-lucide="check" style="width:14px; height:14px;"></i>';
    lucide.createIcons();
    
    setTimeout(() => {
        btn.innerHTML = icon;
        lucide.createIcons();
    }, 2000);
}

function regenerateLast() {
    setPrompt("Please regenerate your previous answer with more detail.");
}

function editUserMessage(btn) {
    const content = btn.closest('.chat-content').querySelector('.chat-bubble').innerText;
    chatInput.value = content;
    chatInput.dispatchEvent(new Event('input')); // trigger height resize
    chatInput.focus();
}


// ── Chat Submission & Streaming ─────────────────────────────────────
chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = chatInput.value.trim();
    if (!message || message.length > 5000) return;

    // Remove welcome state if present
    const welcomeContainer = document.querySelector('.chat-empty-state');
    if (welcomeContainer) welcomeContainer.remove();

    // Reset input
    chatInput.value = '';
    chatInput.style.height = 'auto';
    charCounter.innerText = '0 / 5000';
    sendBtn.disabled = true;

    // Append User Message
    appendMessage('user', message);

    // Append typing indicator
    const aiMessageId = 'msg-' + Date.now();
    appendTypingIndicator(aiMessageId);
    
    scrollToBottom();

    try {
        const response = await fetch('/chat/stream', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ message, session_id: sessionId })
        });

        if (!response.ok) throw new Error('Network response was not ok');

        // Prepare the assistant message bubble
        const msgRow = document.getElementById(aiMessageId);
        msgRow.innerHTML = `
            <div class="chat-message">
                <div class="chat-avatar bg-primary text-white"><i data-lucide="bot"></i></div>
                <div class="chat-content">
                    <div class="chat-bubble markdown-content"></div>
                </div>
            </div>
        `;
        lucide.createIcons();
        
        const bubble = msgRow.querySelector('.chat-bubble');
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let fullContent = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value, {stream: true});
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') {
                        // Stream finished
                        // Apply toolbar
                        const contentDiv = msgRow.querySelector('.chat-content');
                        contentDiv.innerHTML += `
                        <div class="message-toolbar">
                            <button class="btn btn-ghost btn-icon-sm" onclick="copyMessage(this)" title="Copy"><i data-lucide="copy"></i></button>
                            <button class="btn btn-ghost btn-icon-sm" onclick="regenerateLast()" title="Regenerate"><i data-lucide="refresh-cw"></i></button>
                            <button class="btn btn-ghost btn-icon-sm" title="Like"><i data-lucide="thumbs-up"></i></button>
                            <button class="btn btn-ghost btn-icon-sm" title="Dislike"><i data-lucide="thumbs-down"></i></button>
                        </div>`;
                        lucide.createIcons();
                        
                        // Parse markdown if marked is loaded
                        if (typeof marked !== 'undefined') {
                            bubble.innerHTML = marked.parse(fullContent);
                            if (typeof hljs !== 'undefined') hljs.highlightAll();
                        }
                        break;
                    }
                    
                    fullContent += data;
                    if (typeof marked !== 'undefined') {
                        // Append streaming cursor for effect
                        bubble.innerHTML = marked.parse(fullContent) + '<span class="streaming-cursor"></span>';
                    } else {
                        bubble.innerHTML += data + '<span class="streaming-cursor"></span>';
                    }
                    scrollToBottom();
                }
            }
        }
        
        // Remove trailing cursor if any
        const cursor = bubble.querySelector('.streaming-cursor');
        if (cursor) cursor.remove();

    } catch (error) {
        console.error('Chat error:', error);
        const el = document.getElementById(aiMessageId);
        if (el) {
            el.innerHTML = `
                <div class="chat-message">
                    <div class="chat-avatar bg-secondary text-white"><i data-lucide="alert-triangle"></i></div>
                    <div class="chat-content">
                        <div class="chat-bubble" style="color:var(--danger);">Error connecting to AI Coach. Please try again.</div>
                    </div>
                </div>`;
            lucide.createIcons();
        }
    } finally {
        sendBtn.disabled = false;
        chatInput.focus();
    }
});

function appendMessage(role, text) {
    const rowDiv = document.createElement('div');
    rowDiv.className = `chat-message-row ${role}`;
    
    let avatarHtml = '';
    if (role === 'assistant') {
        avatarHtml = `<div class="chat-avatar bg-primary text-white"><i data-lucide="bot"></i></div>`;
    }
    
    // For user, no markdown parse initially for simplicity
    const content = role === 'user' ? text.replace(/\n/g, '<br>') : text;
    
    let toolbar = '';
    if (role === 'user') {
        toolbar = `<div class="message-toolbar">
            <button class="btn btn-ghost btn-icon-sm" onclick="editUserMessage(this)" title="Edit"><i data-lucide="edit-2"></i></button>
        </div>`;
    }
    
    rowDiv.innerHTML = `
        <div class="chat-message">
            ${avatarHtml}
            <div class="chat-content">
                <div class="chat-bubble ${role === 'assistant' ? 'markdown-content' : 'user-bubble'}">${content}</div>
                ${toolbar}
            </div>
        </div>
    `;
    chatMessages.appendChild(rowDiv);
    lucide.createIcons();
}

function appendTypingIndicator(id) {
    const rowDiv = document.createElement('div');
    rowDiv.className = `chat-message-row assistant`;
    rowDiv.id = id;
    rowDiv.innerHTML = `
        <div class="chat-message">
            <div class="chat-avatar bg-primary text-white"><i data-lucide="bot"></i></div>
            <div class="chat-content">
                <div class="chat-bubble">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
    chatMessages.appendChild(rowDiv);
    lucide.createIcons();
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Initial scroll and parse
window.addEventListener('DOMContentLoaded', () => {
    scrollToBottom();
    // Parse existing markdown
    if (typeof marked !== 'undefined') {
        document.querySelectorAll('.chat-message.assistant .chat-bubble').forEach(el => {
            // Check if it's already parsed
            if (!el.innerHTML.includes('<p>')) {
                const raw = el.innerText || el.textContent;
                el.innerHTML = marked.parse(raw);
            }
        });
        if (typeof hljs !== 'undefined') hljs.highlightAll();
    }
    lucide.createIcons();
});
