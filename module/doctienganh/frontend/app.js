/**
 * TOEIC Listening Lab — Main Application
 * Premium SPA with audio player, sentence browser, and word lookup
 */

// ═══════════════ STATE ═══════════════
const state = {
    currentView: 'sentences',
    currentPart: 'all',
    sentences: [],
    playedCount: 0,
    currentAudioText: '',
    isPlaying: false,
    isLoading: false,
    lookupHistory: JSON.parse(localStorage.getItem('lookupHistory') || '[]')
};

// ═══════════════ DOM REFS ═══════════════
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const dom = {
    // Views
    sentencesView: $('#sentences-view'),
    lookupView: $('#lookup-view'),

    // Nav
    navSentences: $('#nav-sentences'),
    navLookup: $('#nav-lookup'),

    // Sentences
    sentencesGrid: $('#sentences-grid'),
    loadingState: $('#loading-state'),
    emptyState: $('#empty-state'),
    statTotal: $('#stat-total'),
    statPlayed: $('#stat-played'),
    statCached: $('#stat-cached'),
    partFilter: $('#part-filter'),

    // Lookup
    lookupInput: $('#lookup-input'),
    charCount: $('#char-count'),
    btnSpeak: $('#btn-speak'),
    voiceSelect: $('#voice-select'),
    historyList: $('#history-list'),

    // Audio Player
    playerBar: $('#audio-player-bar'),
    playerStatus: $('#player-status'),
    playerText: $('#player-text'),
    playerPlay: $('#player-play'),
    playerProgress: $('#player-progress'),
    playerTime: $('#player-time'),
    iconPlay: $('#icon-play'),
    iconPause: $('#icon-pause'),
    iconLoading: $('#icon-loading'),

    // Audio element
    audio: $('#audio-element'),

    // Selection Tooltip
    selectionTooltip: $('#selection-tooltip'),
    btnPlaySelection: $('#btn-play-selection')
};

let isTooltipDismissing = false;

// ═══════════════ INITIALIZATION ═══════════════
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initPartFilter();
    initLookup();
    initAudioPlayer();
    initSelectionTooltip();
    loadSentences();
});

// ═══════════════ NAVIGATION ═══════════════
function initNavigation() {
    $$('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            switchView(view);
        });
    });
}

function switchView(view) {
    state.currentView = view;

    // Update nav buttons
    $$('.nav-btn').forEach(b => b.classList.remove('active'));
    $(`[data-view="${view}"]`).classList.add('active');

    // Update views
    $$('.view').forEach(v => v.classList.remove('active-view'));
    $(`#${view}-view`).classList.add('active-view');
}

// ═══════════════ PART FILTER ═══════════════
function initPartFilter() {
    $$('.filter-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const part = chip.dataset.part;
            state.currentPart = part;

            $$('.filter-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');

            loadSentences();
        });
    });
}

// ═══════════════ SENTENCES ═══════════════
async function loadSentences() {
    dom.loadingState.classList.remove('hidden');
    dom.emptyState.classList.add('hidden');
    dom.sentencesGrid.innerHTML = '';

    try {
        const params = { limit: 100 };
        if (state.currentPart !== 'all') params.part = state.currentPart;

        const data = await api.getSentences(params);
        state.sentences = data.sentences;

        dom.statTotal.textContent = data.total;

        renderSentences(data.sentences);
    } catch (err) {
        console.error('Failed to load sentences:', err);
        showToast('⚠️ Cannot connect to server. Make sure backend is running.');
    } finally {
        dom.loadingState.classList.add('hidden');
    }
}

function renderSentences(sentences) {
    dom.sentencesGrid.innerHTML = '';

    if (sentences.length === 0) {
        dom.emptyState.classList.remove('hidden');
        return;
    }

    sentences.forEach((s, index) => {
        const card = createSentenceCard(s, index);
        dom.sentencesGrid.appendChild(card);
    });
}

function createSentenceCard(sentence, index) {
    const card = document.createElement('div');
    card.className = `sentence-card glass-card`;
    card.style.animationDelay = `${index * 0.05}s`;
    card.dataset.id = sentence.id;

    // Accent color per part
    const accentMap = {
        1: '#6366f1',
        2: '#8b5cf6',
        3: '#06b6d4',
        4: '#10b981'
    };
    card.style.setProperty('--card-accent', accentMap[sentence.part] || '#6366f1');

    card.innerHTML = `
        <div class="card-header">
            <span class="card-part-badge part-${sentence.part}">Part ${sentence.part}</span>
            <button class="card-play-btn" aria-label="Play audio" id="play-btn-${sentence.id}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            </button>
        </div>
        <p class="card-text">${escapeHtml(sentence.text)}</p>
        <span class="card-category">${sentence.category}</span>
        <div class="card-waveform">
            ${Array(8).fill('<div class="wave-bar"></div>').join('')}
        </div>
    `;

    // Click to play
    card.addEventListener('click', (e) => {
        // Prevent full card playback if user was interacting with selection / tooltip
        if (window.getSelection().toString().trim().length > 0 || isTooltipDismissing) return;
        
        if (e.target.closest('.card-play-btn') || e.target === card || card.contains(e.target)) {
            playAudio(sentence.text, sentence.audio_url, sentence.id);
        }
    });

    return card;
}

// ═══════════════ AUDIO PLAYER ═══════════════
function initAudioPlayer() {
    const audio = dom.audio;

    audio.addEventListener('timeupdate', () => {
        if (audio.duration) {
            const pct = (audio.currentTime / audio.duration) * 100;
            dom.playerProgress.style.width = `${pct}%`;
            dom.playerTime.textContent = formatTime(audio.currentTime);
        }
    });

    audio.addEventListener('ended', () => {
        state.isPlaying = false;
        updatePlayerUI('ended');
        clearActiveCards();
    });

    audio.addEventListener('error', () => {
        state.isPlaying = false;
        updatePlayerUI('error');
        showToast('❌ Failed to play audio');
    });

    // Play/pause button
    dom.playerPlay.addEventListener('click', () => {
        if (state.isPlaying) {
            audio.pause();
            state.isPlaying = false;
            updatePlayerUI('paused');
        } else if (audio.src) {
            audio.play();
            state.isPlaying = true;
            updatePlayerUI('playing');
        }
    });

    // Progress bar seeking
    $('#player-progress-wrap').addEventListener('click', (e) => {
        if (audio.duration) {
            const rect = e.currentTarget.querySelector('.player-progress-bar').getBoundingClientRect();
            const pct = (e.clientX - rect.left) / rect.width;
            audio.currentTime = pct * audio.duration;
        }
    });
}

async function playAudio(text, audioUrl, sentenceId) {
    if (state.isLoading) return;

    state.isLoading = true;
    dom.playerBar.classList.add('visible');
    updatePlayerUI('loading');
    dom.playerText.textContent = text;
    state.currentAudioText = text;

    // Highlight active card
    clearActiveCards();
    if (sentenceId) {
        const card = $(`.sentence-card[data-id="${sentenceId}"]`);
        if (card) card.classList.add('playing');
    }

    try {
        let url = audioUrl;

        // If no pre-cached URL or it's from lookup, generate via API
        if (!url || !url.startsWith('/audio/')) {
            const voice = dom.voiceSelect ? dom.voiceSelect.value : 'en-US-AriaNeural';
            const result = await api.textToSpeech(text, voice);
            url = result.url;
            dom.statCached.textContent = result.cached ? '✓ Cached' : '✧ New';
        } else {
            url = `http://localhost:8001${url}`;
            dom.statCached.textContent = '✓ Cached';
        }

        // Play
        dom.audio.src = url;
        await dom.audio.play();
        state.isPlaying = true;
        state.playedCount++;
        dom.statPlayed.textContent = state.playedCount;
        updatePlayerUI('playing');

    } catch (err) {
        console.error('Play failed:', err);
        updatePlayerUI('error');
        showToast(`❌ ${err.message}`);
    } finally {
        state.isLoading = false;
    }
}

function updatePlayerUI(status) {
    dom.iconPlay.classList.add('hidden');
    dom.iconPause.classList.add('hidden');
    dom.iconLoading.classList.add('hidden');

    switch (status) {
        case 'loading':
            dom.iconLoading.classList.remove('hidden');
            dom.playerStatus.textContent = 'Generating...';
            dom.playerPlay.disabled = true;
            break;
        case 'playing':
            dom.iconPause.classList.remove('hidden');
            dom.playerStatus.textContent = 'Now Playing';
            dom.playerPlay.disabled = false;
            break;
        case 'paused':
            dom.iconPlay.classList.remove('hidden');
            dom.playerStatus.textContent = 'Paused';
            dom.playerPlay.disabled = false;
            break;
        case 'ended':
            dom.iconPlay.classList.remove('hidden');
            dom.playerStatus.textContent = 'Finished';
            dom.playerPlay.disabled = false;
            dom.playerProgress.style.width = '100%';
            break;
        case 'error':
            dom.iconPlay.classList.remove('hidden');
            dom.playerStatus.textContent = 'Error';
            dom.playerPlay.disabled = true;
            break;
    }
}

function clearActiveCards() {
    $$('.sentence-card.playing').forEach(c => c.classList.remove('playing'));
}

// ═══════════════ SELECTION TOOLTIP ═══════════════
function initSelectionTooltip() {
    const tooltip = dom.selectionTooltip;
    const btn = dom.btnPlaySelection;
    let selectedText = '';

    document.addEventListener('mouseup', (e) => {
        // Prevent hiding if clicking the tooltip itself
        if (tooltip.contains(e.target)) return;
        
        const mouseX = e.pageX;
        const mouseY = e.pageY;

        setTimeout(() => {
            const selection = window.getSelection();
            let text = selection.toString().trim();
            
            // Fallback for textarea/input which window.getSelection() might miss
            if (!text && (document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'INPUT')) {
                const el = document.activeElement;
                text = el.value.substring(el.selectionStart, el.selectionEnd).trim();
            }

            console.log("Selection text:", text);

            // Validate text (don't show for empty, single char, or super long text)
            if (text.length > 0 && text.length <= 500) {
                selectedText = text;
                const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
                const rect = range ? range.getBoundingClientRect() : {left: 0, top: 0, width: 0};
                
                // Calculate position relative to document
                let x = rect.left + rect.width / 2 + window.scrollX;
                let y = rect.top + window.scrollY;
                
                // Fallback for Textarea where range rect is 0,0
                if (rect.width === 0 && rect.left === 0) {
                    x = mouseX;
                    y = mouseY - 10; // Shift up slightly from cursor
                }
                
                console.log("Showing tooltip at", x, y, tooltip);

                tooltip.style.left = `${x}px`;
                tooltip.style.top = `${y}px`;
                tooltip.style.display = 'flex'; // force fallback
                tooltip.classList.add('show');
            } else {
                console.log("Hiding tooltip");
                tooltip.classList.remove('show');
            }
        }, 10);
    });

    document.addEventListener('mousedown', (e) => {
        if (!tooltip.contains(e.target)) {
            if (tooltip.classList.contains('show')) {
                isTooltipDismissing = true;
                setTimeout(() => isTooltipDismissing = false, 200); // clear after click event passes
            }
            tooltip.classList.remove('show');
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            tooltip.classList.remove('show');
            window.getSelection().removeAllRanges();
        }
    });

    // Play action
    btn.addEventListener('click', async () => {
        if (!selectedText) return;
        
        btn.classList.add('generating');
        btn.innerHTML = `<div class="loading-spinner" style="width:14px;height:14px;border-width:2px;display:inline-block"></div><span>Loading...</span>`;
        
        try {
            await playAudio(selectedText, null, null);
        } finally {
            btn.classList.remove('generating');
            btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg><span>Listen</span>`;
        }
    });
}

// ═══════════════ WORD LOOKUP ═══════════════
function initLookup() {
    const input = dom.lookupInput;
    const btn = dom.btnSpeak;

    // Character counter
    input.addEventListener('input', () => {
        const len = input.value.length;
        dom.charCount.textContent = `${len} / 500`;
        btn.disabled = len === 0;

        // Warn if close to limit
        if (len > 450) {
            dom.charCount.style.color = 'var(--accent-rose)';
        } else {
            dom.charCount.style.color = '';
        }
    });

    // Enter key to speak
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (input.value.trim()) handleSpeak();
        }
    });

    // Speak button
    btn.addEventListener('click', handleSpeak);

    // Render history
    renderHistory();
}

async function handleSpeak() {
    const text = dom.lookupInput.value.trim();
    if (!text) return;

    dom.btnSpeak.classList.add('loading');
    dom.btnSpeak.innerHTML = `
        <div class="loading-spinner" style="width:16px;height:16px;border-width:2px;"></div>
        Generating...
    `;

    try {
        const voice = dom.voiceSelect.value;
        await playAudio(text, null, null);

        // Add to history
        addToHistory(text, voice);

    } catch (err) {
        showToast(`❌ ${err.message}`);
    } finally {
        dom.btnSpeak.classList.remove('loading');
        dom.btnSpeak.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/></svg>
            Speak
        `;
    }
}

function addToHistory(text, voice) {
    // Remove duplicate
    state.lookupHistory = state.lookupHistory.filter(h => h.text !== text);

    // Add to front
    state.lookupHistory.unshift({ text, voice, timestamp: Date.now() });

    // Limit to 20 items
    if (state.lookupHistory.length > 20) {
        state.lookupHistory = state.lookupHistory.slice(0, 20);
    }

    // Save
    localStorage.setItem('lookupHistory', JSON.stringify(state.lookupHistory));
    renderHistory();
}

function renderHistory() {
    const list = dom.historyList;

    if (state.lookupHistory.length === 0) {
        list.innerHTML = '<p class="history-empty">Your lookup history will appear here</p>';
        return;
    }

    list.innerHTML = state.lookupHistory.map(item => `
        <div class="history-item" data-text="${escapeAttr(item.text)}" data-voice="${item.voice}">
            <button class="history-item-play" aria-label="Play">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            </button>
            <span class="history-item-text">${escapeHtml(item.text)}</span>
            <span class="history-item-voice">${getVoiceShortName(item.voice)}</span>
        </div>
    `).join('');

    // Bind click events
    list.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => {
            const text = item.dataset.text;
            dom.lookupInput.value = text;
            dom.charCount.textContent = `${text.length} / 500`;
            dom.btnSpeak.disabled = false;
            playAudio(text, null, null);
        });
    });
}

function getVoiceShortName(voice) {
    const map = {
        'en-US-AriaNeural': 'US♀',
        'en-US-GuyNeural': 'US♂',
        'en-GB-SoniaNeural': 'UK♀',
        'en-GB-RyanNeural': 'UK♂',
        'en-AU-NatashaNeural': 'AU♀'
    };
    return map[voice] || voice.split('-')[1];
}

// ═══════════════ UTILITIES ═══════════════
function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function escapeAttr(text) {
    return text.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// Toast notification
function showToast(message, duration = 3000) {
    let toast = document.querySelector('.toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('show');

    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}
