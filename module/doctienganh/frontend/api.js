/**
 * API Service Layer — communicates with TOEIC TTS Backend
 */

const API_BASE = 'http://localhost:8001';

const api = {
    /**
     * Generate or fetch cached TTS audio
     * @param {string} text - Text to convert
     * @param {string} voice - Voice ID
     * @returns {Promise<{url: string, cached: boolean, text: string, hash: string}>}
     */
    async textToSpeech(text, voice = 'en-US-AriaNeural') {
        const res = await fetch(`${API_BASE}/api/tts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, voice })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        // Convert relative URL to absolute
        data.url = `${API_BASE}${data.url}`;
        return data;
    },

    /**
     * Fetch TOEIC sentences
     * @param {object} params - { part, page, limit }
     * @returns {Promise<{sentences: Array, total: number, page: number, pages: number}>}
     */
    async getSentences(params = {}) {
        const query = new URLSearchParams();
        if (params.part && params.part !== 'all') query.set('part', params.part);
        if (params.page) query.set('page', params.page);
        if (params.limit) query.set('limit', params.limit);

        const res = await fetch(`${API_BASE}/api/sentences?${query}`);
        if (!res.ok) throw new Error(`Failed to load sentences: HTTP ${res.status}`);
        return res.json();
    },

    /**
     * Get available parts summary
     * @returns {Promise<{parts: Array}>}
     */
    async getParts() {
        const res = await fetch(`${API_BASE}/api/parts`);
        if (!res.ok) throw new Error('Failed to load parts');
        return res.json();
    },

    /**
     * Get available voices
     * @returns {Promise<{voices: Array}>}
     */
    async getVoices() {
        const res = await fetch(`${API_BASE}/api/voices`);
        if (!res.ok) throw new Error('Failed to load voices');
        return res.json();
    },

    /**
     * Health check
     */
    async health() {
        const res = await fetch(`${API_BASE}/health`);
        return res.json();
    }
};
