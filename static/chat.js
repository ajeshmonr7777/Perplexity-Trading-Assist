document.addEventListener('DOMContentLoaded', () => {
    // Initial setup
    const input = document.getElementById('chat-input');
    input.focus();
});

let includeHoldings = false;
let youtubeMode = false;

function toggleHoldings() {
    includeHoldings = !includeHoldings;
    const btn = document.getElementById('holdings-toggle');
    if (includeHoldings) {
        btn.classList.add('active');
        btn.querySelector('i').style.color = '#10b981';
    } else {
        btn.classList.remove('active');
        btn.querySelector('i').style.color = '';
    }
}

function toggleYoutubeInput() {
    youtubeMode = !youtubeMode;
    const wrapper = document.getElementById('youtube-wrapper');
    const input = document.getElementById('youtube-url');

    if (youtubeMode) {
        wrapper.style.display = 'flex';
        input.focus();
    } else {
        wrapper.style.display = 'none';
        input.value = ''; // Clear but keep mode logic clean
    }
}

function clearYoutube() {
    document.getElementById('youtube-url').value = '';
    toggleYoutubeInput(); // Close it
}

function handleEnter(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
    }
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const youtubeInput = document.getElementById('youtube-url');

    const text = input.value.trim();
    if (!text) return;

    // Get YouTube URL if active
    const youtubeUrl = youtubeMode ? youtubeInput.value.trim() : null;

    // Clear Inputs
    input.value = '';
    if (youtubeUrl) {
        youtubeInput.value = '';
        toggleYoutubeInput(); // Close wrapper
    }

    // Add User Message
    addMessage(text, 'user', youtubeUrl);

    // Show Loading
    const loadingId = showLoading();

    try {
        const response = await fetch('/api/ai/query-assistant', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: text,
                include_holdings: includeHoldings,
                youtube_url: youtubeUrl
            })
        });

        const data = await response.json();

        // Check for error
        if (data.error || (data.detail && typeof data.detail === 'string')) {
            throw new Error(data.error || data.detail);
        }

        removeLoading(loadingId);
        addMessage(data.response, 'system');

    } catch (error) {
        removeLoading(loadingId);
        addMessage(`Error: ${error.message}`, 'system');
        console.error(error);
    }
}

function addMessage(text, type, metadata = null) {
    const history = document.getElementById('chat-history');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${type}`;

    let content = '';

    // Add metadata badges
    if (metadata) { // YouTube URL
        content += `<div class="video-badge"><i class="fa-brands fa-youtube"></i> Analyzed Video</div>`;
    }

    // Format text
    if (type === 'system') {
        // Use marked.js if available
        if (typeof marked !== 'undefined' && marked.parse) {
            content += marked.parse(text);
        } else {
            content += `<p>${text}</p>`;
        }
    } else {
        content += `<p>${text}</p>`;
    }

    msgDiv.innerHTML = content;
    history.appendChild(msgDiv);
    history.scrollTop = history.scrollHeight;
}

function showLoading() {
    const history = document.getElementById('chat-history');
    const id = 'loading-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = 'message system';
    div.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Thinking...';
    history.appendChild(div);
    history.scrollTop = history.scrollHeight;
    return id;
}

function removeLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
