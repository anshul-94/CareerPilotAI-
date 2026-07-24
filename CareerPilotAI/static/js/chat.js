/* ============================================
   CareerPilot AI — Chat JavaScript
   AI Career Coach chat interface with typing animation
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    initChat();
});

function initChat() {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const messagesContainer = document.getElementById('chatMessages');
    
    if (!chatForm || !chatInput) return;

    // Send message on form submit
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        sendMessage();
    });

    // Send on Enter (but allow Shift+Enter for newline)
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Auto-resize textarea
    chatInput.addEventListener('input', () => {
        chatInput.style.height = 'auto';
        chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });

    // Suggestion buttons
    document.querySelectorAll('.chat-suggestion-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            chatInput.value = btn.textContent;
            sendMessage();
        });
    });

    // Scroll to bottom on load
    scrollToBottom();
}

async function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const messagesContainer = document.getElementById('chatMessages');
    const sessionId = document.getElementById('sessionId')?.value;
    
    const message = chatInput.value.trim();
    if (!message) return;

    // Clear input
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Add user message
    appendMessage('user', message);
    scrollToBottom();

    // Show typing indicator
    const typingId = showTypingIndicator();

    try {
        const data = await CareerPilot.api('/chat/send', {
            method: 'POST',
            body: { message, session_id: sessionId }
        });

        // Remove typing indicator
        removeTypingIndicator(typingId);

        if (data.success) {
            // Animate the response
            await typeMessage(data.response_html || data.response);
            
            // Update suggestions
            updateSuggestions(data.suggested_questions || []);
        }
    } catch (error) {
        removeTypingIndicator(typingId);
        appendMessage('assistant', 'Sorry, I encountered an error. Please try again.');
    }

    scrollToBottom();
}

function appendMessage(role, content) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    const isUser = role === 'user';
    const avatar = isUser ? '👤' : '🤖';
    
    const messageEl = document.createElement('div');
    messageEl.className = `chat-message ${role}`;
    messageEl.innerHTML = `
        <div class="chat-avatar">${avatar}</div>
        <div class="chat-bubble">${isUser ? escapeHtml(content) : content}</div>
    `;
    
    container.appendChild(messageEl);
}

async function typeMessage(htmlContent) {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    const messageEl = document.createElement('div');
    messageEl.className = 'chat-message assistant';
    messageEl.innerHTML = `
        <div class="chat-avatar">🤖</div>
        <div class="chat-bubble"></div>
    `;
    container.appendChild(messageEl);

    const bubble = messageEl.querySelector('.chat-bubble');
    
    // For HTML content, just set it directly with a fade effect
    bubble.style.opacity = '0';
    bubble.innerHTML = htmlContent;
    
    // Animate opacity
    requestAnimationFrame(() => {
        bubble.style.transition = 'opacity 0.5s ease';
        bubble.style.opacity = '1';
    });

    scrollToBottom();
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    const id = 'typing-' + Date.now();
    
    const el = document.createElement('div');
    el.id = id;
    el.className = 'chat-message assistant';
    el.innerHTML = `
        <div class="chat-avatar">🤖</div>
        <div class="chat-bubble">
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    container.appendChild(el);
    scrollToBottom();
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

function updateSuggestions(suggestions) {
    const container = document.querySelector('.chat-suggestions');
    if (!container || !suggestions.length) return;

    container.innerHTML = suggestions.map(s => 
        `<button class="chat-suggestion-btn" onclick="document.getElementById('chatInput').value='${escapeHtml(s)}';sendMessage();">${escapeHtml(s)}</button>`
    ).join('');
}

function scrollToBottom() {
    const container = document.getElementById('chatMessages');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
