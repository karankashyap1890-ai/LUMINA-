/**
 * Lumina AI — Frontend Application
 * WebSocket-based real-time chat with skill selection and markdown rendering.
 */

// ── Config ─────────────────────────────────────────────────────────────────
const API_BASE  = window.location.origin;
const WS_BASE   = API_BASE.replace(/^http/, 'ws');
const SESSION_ID = Math.random().toString(36).slice(2, 10);

// ── Skill metadata ──────────────────────────────────────────────────────────
const SKILLS = {
  auto:         { icon: '🌟', name: 'Auto-detect',  color: '#22d3ee' },
  data:         { icon: '📊', name: 'Data Analysis', color: '#f59e0b' },
  code:         { icon: '💻', name: 'Code Assistant',color: '#10b981' },
  schedule:     { icon: '📅', name: 'Scheduler',     color: '#6366f1' },
  learn:        { icon: '🎓', name: 'Learning Mode', color: '#ec4899' },
  troubleshoot: { icon: '🔧', name: 'Troubleshoot',  color: '#ef4444' },
};

// ── State ───────────────────────────────────────────────────────────────────
let ws            = null;
let currentSkill  = 'auto';
let isTyping      = false;
let reconnectTimer = null;
let reconnectAttempts = 0;
const MAX_RECONNECT = 5;

// ── DOM references ──────────────────────────────────────────────────────────
const messagesEl     = document.getElementById('messages');
const inputEl        = document.getElementById('messageInput');
const sendBtnEl      = document.getElementById('sendBtn');
const typingEl       = document.getElementById('typingIndicator');
const typingLabelEl  = document.getElementById('typingLabel');
const statusDotEl    = document.getElementById('statusDot');
const statusTextEl   = document.getElementById('statusText');
const chatTitleEl    = document.getElementById('chatTitle');
const chatSubtitleEl = document.getElementById('chatSubtitle');
const skillPillIcon  = document.getElementById('skillPillIcon');
const skillPillName  = document.getElementById('skillPillName');
const toastEl        = document.getElementById('toastContainer');
const sidebarEl      = document.getElementById('sidebar');

// ── WebSocket ───────────────────────────────────────────────────────────────

function connectWS() {
  const url = `${WS_BASE}/ws/${SESSION_ID}`;
  ws = new WebSocket(url);

  ws.onopen = () => {
    setStatus('connected', '🟢 Connected');
    reconnectAttempts = 0;
    clearTimeout(reconnectTimer);
    showToast('Connected to Lumina', 'success');
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleServerMessage(msg);
    } catch (e) {
      console.error('WS parse error:', e);
    }
  };

  ws.onerror = () => {
    setStatus('error', '🔴 Error');
  };

  ws.onclose = () => {
    setStatus('disconnected', '⚪ Disconnected');
    hideTyping();
    if (reconnectAttempts < MAX_RECONNECT) {
      const delay = Math.min(2000 * Math.pow(2, reconnectAttempts), 30000);
      reconnectAttempts++;
      showToast(`Reconnecting in ${delay / 1000}s…`, 'info');
      reconnectTimer = setTimeout(connectWS, delay);
    } else {
      showToast('Connection lost. Refresh to reconnect.', 'error');
    }
  };
}

function handleServerMessage(msg) {
  if (msg.type === 'typing') {
    const skill = msg.agent || currentSkill;
    const s = SKILLS[skill] || SKILLS.auto;
    typingLabelEl.textContent = `${s.icon} ${s.name} is thinking…`;
    showTyping();
  } else if (msg.type === 'response') {
    hideTyping();
    appendAgentMessage(msg.data);
  } else if (msg.type === 'error') {
    hideTyping();
    appendAgentMessage({
      content: `⚠️ ${msg.message}`,
      agent_name: 'System',
      skill: 'error',
      tools_used: [],
    });
  }
}

// ── Sending ─────────────────────────────────────────────────────────────────

function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  appendUserMessage(text);
  inputEl.value = '';
  autoResizeTextarea();

  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ message: text, skill: currentSkill }));
    showTyping();
  } else {
    // Fallback: REST API
    sendViaREST(text);
  }
}

async function sendViaREST(text) {
  try {
    const resp = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, skill: currentSkill }),
    });
    const data = await resp.json();
    hideTyping();
    if (resp.ok) {
      appendAgentMessage(data);
    } else {
      appendAgentMessage({ content: `❌ ${data.detail}`, agent_name: 'System', skill: 'error', tools_used: [] });
    }
  } catch (err) {
    hideTyping();
    appendAgentMessage({ content: '❌ Could not reach the Lumina API.', agent_name: 'System', skill: 'error', tools_used: [] });
  }
}

// ── Message rendering ───────────────────────────────────────────────────────

function appendUserMessage(text) {
  const el = document.createElement('div');
  el.className = 'message user';
  el.innerHTML = `
    <div class="avatar user-avatar">👤</div>
    <div class="bubble user-bubble">
      <div class="bubble-content">${escapeHtml(text)}</div>
    </div>
  `;
  messagesEl.appendChild(el);
  scrollToBottom();
}

function appendAgentMessage(data) {
  const skill    = data.skill || 'auto';
  const skillMeta = SKILLS[skill] || SKILLS.auto;
  const tools    = data.tools_used || [];
  const content  = renderMarkdown(data.content || '');

  const el = document.createElement('div');
  el.className = 'message agent';
  el.innerHTML = `
    <div class="avatar agent-avatar">${skillMeta.icon}</div>
    <div class="bubble agent-bubble">
      <div class="bubble-meta">
        <span class="agent-name">${escapeHtml(data.agent_name || 'Lumina')}</span>
        <span class="skill-badge ${skill}">${skill}</span>
      </div>
      <div class="bubble-content">${content}</div>
      ${tools.length ? `
        <div class="tools-used">
          <span class="tools-label">TOOLS:</span>
          ${tools.map(t => `<span class="tool-chip">${t}</span>`).join('')}
        </div>
      ` : ''}
    </div>
  `;
  messagesEl.appendChild(el);
  scrollToBottom();
}

// ── Markdown renderer (lightweight) ────────────────────────────────────────

function renderMarkdown(text) {
  // Escape HTML first, then selectively restore markdown constructs
  let html = escapeHtml(text);

  // Code blocks (``` ... ```)
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre><code class="lang-${lang}">${code.trim()}</code></pre>`
  );

  // Inline code
  html = html.replace(/`([^`\n]+)`/g, '<code>$1</code>');

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

  // Italic
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.+?)_/g, '<em>$1</em>');

  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm,  '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm,   '<h1>$1</h1>');

  // Horizontal rule
  html = html.replace(/^---$/gm, '<hr>');

  // Blockquote
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

  // Tables (basic)
  html = html.replace(/^\|(.+)\|$/gm, (line) => {
    const cells = line.split('|').slice(1, -1).map(c => c.trim());
    return '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
  });
  html = html.replace(/(<tr>.*<\/tr>\n)+/gs, match => `<table>${match}</table>`);
  // Make first row of table a header
  html = html.replace(/<table>(<tr>)(.*?)(<\/tr>)/s, (m, open, inner, close) => {
    const headerRow = inner.replace(/<td>/g, '<th>').replace(/<\/td>/g, '</th>');
    return `<table>${open}${headerRow}${close}`;
  });

  // Unordered lists
  html = html.replace(/(^[\s]*[-*+] .+(?:\n|$))+/gm, match => {
    const items = match.trim().split('\n').map(l => `<li>${l.replace(/^[\s]*[-*+] /, '')}</li>`).join('');
    return `<ul>${items}</ul>`;
  });

  // Ordered lists
  html = html.replace(/(^[\s]*\d+\. .+(?:\n|$))+/gm, match => {
    const items = match.trim().split('\n').map(l => `<li>${l.replace(/^[\s]*\d+\. /, '')}</li>`).join('');
    return `<ol>${items}</ol>`;
  });

  // Paragraphs (double newlines → <p>)
  html = html.split(/\n{2,}/).map(block => {
    if (/^<(h[123]|ul|ol|pre|table|hr|blockquote)/.test(block)) return block;
    return `<p>${block.replace(/\n/g, '<br>')}</p>`;
  }).join('\n');

  return html;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Skill selection ─────────────────────────────────────────────────────────

function setSkill(skill) {
  currentSkill = skill;
  const s = SKILLS[skill] || SKILLS.auto;

  // Update sidebar buttons
  document.querySelectorAll('.skill-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.skill === skill);
  });

  // Update header
  chatTitleEl.textContent  = `${s.icon} Lumina — ${s.name}`;
  chatSubtitleEl.textContent = `Skill: ${skill}`;

  // Update input pill
  skillPillIcon.textContent = s.icon;
  skillPillName.textContent = s.name;
}

// ── UI helpers ──────────────────────────────────────────────────────────────

function setStatus(state, text) {
  statusDotEl.className = 'status-dot ' + state;
  statusTextEl.textContent = text;
}

function showTyping() {
  typingEl.classList.remove('hidden');
  messagesEl.scrollTop = messagesEl.scrollHeight;
}
function hideTyping() {
  typingEl.classList.add('hidden');
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  });
}

function showToast(message, type = 'info', duration = 3000) {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  toastEl.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'toast-out 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function autoResizeTextarea() {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 160) + 'px';
}

// ── Welcome screen ──────────────────────────────────────────────────────────

function renderWelcome() {
  const el = document.createElement('div');
  el.className = 'welcome-card';
  el.innerHTML = `
    <h1 class="welcome-title">Welcome to Lumina ✦</h1>
    <p class="welcome-subtitle">Your full-stack multi-agent AI system. Select a skill or start typing.</p>
    <div class="skill-grid">
      ${Object.entries(SKILLS).filter(([k]) => k !== 'auto').map(([key, s]) => `
        <div class="skill-card" data-skill="${key}">
          <span class="skill-card-icon">${s.icon}</span>
          <div>
            <div class="skill-card-title">${s.name}</div>
            <div class="skill-card-desc">${getSkillDesc(key)}</div>
          </div>
        </div>
      `).join('')}
    </div>
  `;

  el.querySelectorAll('.skill-card').forEach(card => {
    card.addEventListener('click', () => {
      setSkill(card.dataset.skill);
      inputEl.focus();
    });
  });

  messagesEl.appendChild(el);
}

function getSkillDesc(skill) {
  return {
    data:         'CSV analysis, statistics, chart specs',
    code:         'Code review, debugging, safe execution',
    schedule:     'Reminders, tasks, NL time parsing',
    learn:        'Adaptive explanations for any level',
    troubleshoot: 'Root-cause analysis & fix strategies',
  }[skill] || '';
}

// ── Event listeners ─────────────────────────────────────────────────────────

// Send on Enter (Shift+Enter = newline)
inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
  // Ctrl+K → insert code block
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const pos = inputEl.selectionStart;
    const before = inputEl.value.slice(0, pos);
    const after  = inputEl.value.slice(pos);
    inputEl.value = before + '```python\n\n```' + after;
    inputEl.selectionStart = inputEl.selectionEnd = pos + 10;
    autoResizeTextarea();
  }
});

inputEl.addEventListener('input', autoResizeTextarea);

sendBtnEl.addEventListener('click', sendMessage);

// Skill buttons
document.querySelectorAll('.skill-btn').forEach(btn => {
  btn.addEventListener('click', () => setSkill(btn.dataset.skill));
});

// Quick prompts
document.querySelectorAll('.quick-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    inputEl.value = btn.dataset.prompt;
    autoResizeTextarea();
    inputEl.focus();
  });
});

// Skill pill click → cycle skills
document.getElementById('currentSkillPill').addEventListener('click', () => {
  const skills = Object.keys(SKILLS);
  const idx = skills.indexOf(currentSkill);
  setSkill(skills[(idx + 1) % skills.length]);
});

// Clear chat
document.getElementById('clearBtn').addEventListener('click', () => {
  messagesEl.innerHTML = '';
  renderWelcome();
  showToast('Chat cleared', 'info');
});

// Mobile sidebar toggle
document.getElementById('sidebarToggle').addEventListener('click', () => {
  sidebarEl.classList.toggle('open');
});
// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
  if (window.innerWidth <= 768 && sidebarEl.classList.contains('open')) {
    if (!sidebarEl.contains(e.target) && e.target.id !== 'sidebarToggle') {
      sidebarEl.classList.remove('open');
    }
  }
});

// Theme toggle (light/dark placeholder)
document.getElementById('themeBtn').addEventListener('click', () => {
  showToast('Light theme coming soon!', 'info');
});

// ── Boot ────────────────────────────────────────────────────────────────────

(function init() {
  renderWelcome();
  setSkill('auto');
  setStatus('connecting', '⚪ Connecting…');
  connectWS();
  inputEl.focus();
})();
