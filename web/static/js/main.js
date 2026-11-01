/**
 * AI Job Application Assistant — Frontend JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    // Escape key closes modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeApplyModal();
        }
    });

    // Close modal when clicking outside dialog
    const modal = document.getElementById('applyModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeApplyModal();
            }
        });
    }
});

/**
 * Filter vacancies on Jobs page
 */
function filterJobs() {
    const searchInput = document.getElementById('jobSearchInput');
    const verdictFilter = document.getElementById('verdictFilter');
    if (!searchInput || !verdictFilter) return;

    const query = searchInput.value.toLowerCase().trim();
    const verdict = verdictFilter.value;

    const cards = document.querySelectorAll('#jobsContainer .job-card');
    cards.forEach(card => {
        const text = (card.getAttribute('data-text') || '').toLowerCase();
        const cardVerdict = card.getAttribute('data-verdict') || '';
        const cardGate = card.getAttribute('data-gate') || '';

        const matchesQuery = query === '' || text.includes(query);
        let matchesVerdict = true;

        if (verdict === 'FAIL') {
            matchesVerdict = cardGate === 'FAIL';
        } else if (verdict !== 'all') {
            matchesVerdict = cardVerdict === verdict && cardGate !== 'FAIL';
        }

        if (matchesQuery && matchesVerdict) {
            card.style.display = '';
        } else {
            card.style.display = 'none';
        }
    });
}

/**
 * Trigger job search via agent workflow
 */
async function triggerJobSearch() {
    const btn = document.getElementById('findJobsBtn');
    const originalText = btn ? btn.innerHTML : '';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-small"></span> Searching & Ranking...';
    }

    try {
        const resp = await fetch('/api/jobs/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await resp.json();
        if (data.status === 'ok') {
            alert(`Discovery complete: ${data.message || 'Updated seen_jobs.json'}`);
            window.location.reload();
        } else {
            alert(`Error running search: ${data.error || 'Unknown error'}`);
        }
    } catch (err) {
        console.error('Failed to trigger job search:', err);
        alert('Failed to connect to agent backend.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = originalText;
        }
    }
}

/**
 * Open Application Dry-Run Modal
 */
async function openApplyDryrun(jobKey) {
    const modal = document.getElementById('applyModal');
    const modalTitle = document.getElementById('modalCompanyTitle');
    const modalBody = document.getElementById('modalBody');

    if (!modal || !modalBody) return;

    modal.style.display = 'flex';
    modalTitle.textContent = 'Application Draft (Generating...)';
    modalBody.innerHTML = `
        <div style="text-align: center; padding: 40px;">
            <div class="loading-spinner"></div>
            <p style="margin-top: 15px; color: var(--text-muted);">Generating grounded application artifacts for <code>${escapeHtml(jobKey)}</code>...</p>
        </div>
    `;

    try {
        const resp = await fetch(`/api/jobs/apply-dryrun/${encodeURIComponent(jobKey)}`);
        if (!resp.ok) {
            throw new Error(`Server returned HTTP ${resp.status}`);
        }
        const data = await resp.json();

        if (data.error) {
            modalBody.innerHTML = `<div class="alert alert-warning">${escapeHtml(data.error)}</div>`;
            return;
        }

        const draft = data.draft;
        const job = draft.job;

        modalTitle.textContent = `${job.company} — ${job.title}`;

        const scoreClass = job.score >= 75 ? 'score-strong' : (job.score >= 60 ? 'score-good' : 'score-mod');

        modalBody.innerHTML = `
            <div class="draft-header-summary">
                <div class="draft-stat">
                    <span class="draft-stat-lbl">Evaluation Score</span>
                    <span class="score-badge ${scoreClass}">${job.score}/100</span>
                </div>
                <div class="draft-stat">
                    <span class="draft-stat-lbl">Verdict</span>
                    <span class="badge badge-primary">${escapeHtml(job.verdict)}</span>
                </div>
                <div class="draft-stat">
                    <span class="draft-stat-lbl">Language Gate</span>
                    <span class="badge badge-success">${escapeHtml(job.language_gate || 'PASS')}</span>
                </div>
                <div class="draft-stat">
                    <span class="draft-stat-lbl">Execution Mode</span>
                    <span class="badge badge-subtle">DRY RUN (No auto-submit)</span>
                </div>
            </div>

            <div class="draft-section">
                <h4>🎯 Tailored Professional Summary (for CV):</h4>
                <div class="draft-box">
                    <p>${escapeHtml(draft.tailored_summary)}</p>
                </div>
            </div>

            <div class="draft-section">
                <h4>⚡ Highlighted Competencies & Matching Projects:</h4>
                <div class="tag-cloud" style="margin-bottom: 10px;">
                    ${draft.matching_skills.map(s => `<span class="tag tag-tech">✓ ${escapeHtml(s)}</span>`).join('')}
                </div>
                <ul class="bullet-list">
                    ${draft.matching_projects.map(p => `<li>${escapeHtml(p)}</li>`).join('')}
                </ul>
            </div>

            <div class="draft-section">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h4 style="margin: 0;">✉️ Tailored Cover Letter Draft:</h4>
                    <button class="btn btn-outline btn-xs" onclick="copyCoverLetter()">📋 Copy Cover Letter</button>
                </div>
                <textarea id="coverLetterText" class="cover-letter-area" readonly rows="12">${escapeHtml(draft.cover_letter)}</textarea>
            </div>

            <div class="draft-section">
                <h4>🔒 Factual Grounding Verification:</h4>
                <div class="checklist">
                    ${draft.grounding_checklist.map(item => `
                        <div class="check-item">
                            <span class="check-icon">✓</span>
                            <span>${escapeHtml(item)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } catch (err) {
        console.error('Failed to load application draft:', err);
        modalBody.innerHTML = `<div class="alert alert-warning">Failed to load application draft: ${escapeHtml(err.message)}</div>`;
    }
}

/**
 * Close Application Dry-Run Modal
 */
function closeApplyModal() {
    const modal = document.getElementById('applyModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Copy Cover Letter text to clipboard
 */
function copyCoverLetter() {
    const textarea = document.getElementById('coverLetterText');
    if (!textarea) return;
    navigator.clipboard.writeText(textarea.value).then(() => {
        alert('Cover letter copied to clipboard!');
    }).catch(err => {
        textarea.select();
        document.execCommand('copy');
        alert('Cover letter copied to clipboard!');
    });
}

/**
 * Dispatch agent command from terminal
 */
async function dispatchCommand() {
    const input = document.getElementById('terminalInput');
    const terminal = document.getElementById('terminalOutput');
    if (!input || !terminal) return;

    const command = input.value.trim();
    if (!command) return;

    // Display user command
    const userLine = document.createElement('div');
    userLine.className = 'terminal-line user';
    userLine.textContent = `> ${command}`;
    terminal.appendChild(userLine);

    input.value = '';

    // Thinking indicator
    const thinkingLine = document.createElement('div');
    thinkingLine.className = 'terminal-line system';
    thinkingLine.innerHTML = '<em>Agent thinking...</em>';
    terminal.appendChild(thinkingLine);
    terminal.scrollTop = terminal.scrollHeight;

    try {
        const resp = await fetch('/api/agent/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command })
        });
        const data = await resp.json();

        terminal.removeChild(thinkingLine);

        const agentLine = document.createElement('div');
        agentLine.className = 'terminal-line agent';
        agentLine.textContent = data.response || 'Action completed.';
        terminal.appendChild(agentLine);

        // If extra lines or details exist
        if (data.details) {
            const detailLine = document.createElement('div');
            detailLine.className = 'terminal-line details';
            detailLine.textContent = data.details;
            terminal.appendChild(detailLine);
        }

        // Add to recent activity table dynamically if on page
        const logBody = document.getElementById('actionLogBody');
        if (logBody && data.action) {
            const tr = document.createElement('tr');
            const now = new Date().toLocaleTimeString('en-GB');
            tr.innerHTML = `<td><code>${now}</code></td><td><strong>${escapeHtml(data.action)}</strong></td><td>${escapeHtml(data.response || '')}</td>`;
            logBody.insertBefore(tr, logBody.firstChild);
        }
    } catch (err) {
        if (thinkingLine.parentNode === terminal) {
            terminal.removeChild(thinkingLine);
        }
        const errLine = document.createElement('div');
        errLine.className = 'terminal-line error';
        errLine.textContent = `Error: ${err.message}`;
        terminal.appendChild(errLine);
    }

    terminal.scrollTop = terminal.scrollHeight;
}

/**
 * Quick send from terminal suggestions
 */
function sendQuickCommand(cmd) {
    const input = document.getElementById('terminalInput');
    if (input) {
        input.value = cmd;
        dispatchCommand();
    }
}

/**
 * Toggle raw markdown view in profile
 */
function toggleRawView() {
    const container = document.getElementById('rawMarkdownContainer');
    if (!container) return;
    if (container.style.display === 'none' || container.style.display === '') {
        container.style.display = 'block';
    } else {
        container.style.display = 'none';
    }
}

/**
 * Helper to escape HTML characters
 */
function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}

