/* ============================================
   CareerPilot AI — Resume JavaScript
   Upload drag & drop, analysis display, builder
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    initUploadZone();
    initAnalysis();
    initScoreCircles();
});

// ── Drag & Drop Upload ──────────────────────────
function initUploadZone() {
    const zone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('resumeFile');
    if (!zone || !fileInput) return;

    zone.addEventListener('click', () => fileInput.click());
    
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('drag-over');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('drag-over');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelect(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
}

function handleFileSelect(file) {
    if (file.type !== 'application/pdf') {
        CareerPilot.showNotification('Only PDF files are allowed', 'danger');
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        CareerPilot.showNotification('File size must be less than 10MB', 'danger');
        return;
    }

    const zone = document.getElementById('uploadZone');
    zone.innerHTML = `
        <div style="color: var(--success); font-size: 2rem; margin-bottom: 0.75rem;">📄</div>
        <h3>${file.name}</h3>
        <p>${(file.size / 1024).toFixed(1)} KB</p>
        <p style="color: var(--success); margin-top: 0.5rem;">✓ Ready to upload</p>
    `;

    // Auto-submit
    const form = document.getElementById('uploadForm');
    if (form) form.submit();
}

// ── Resume Analysis ─────────────────────────────
function initAnalysis() {
    const analyzeBtn = document.getElementById('analyzeBtn');
    if (!analyzeBtn) return;

    analyzeBtn.addEventListener('click', async () => {
        const resumeId = analyzeBtn.dataset.resumeId;
        const targetRole = document.getElementById('targetRole')?.value || '';
        
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="spinner spinner-sm"></span> Analyzing...';
        
        const resultsContainer = document.getElementById('analysisResults');
        if (resultsContainer) {
            CareerPilot.showAIProcessing(resultsContainer, 'AI is analyzing your resume...');
        }

        try {
            const data = await CareerPilot.api('/resume/analyze/run', {
                method: 'POST',
                body: { resume_id: parseInt(resumeId), target_role: targetRole }
            });

            if (data.success) {
                displayAnalysis(data.analysis);
                CareerPilot.showNotification('Resume analysis complete!', 'success');
            }
        } catch (error) {
            CareerPilot.showNotification('Analysis failed. Please try again.', 'danger');
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '🔍 Analyze Resume';
            CareerPilot.hideAIProcessing();
        }
    });
}

function displayAnalysis(analysis) {
    const container = document.getElementById('analysisResults');
    if (!container) return;

    container.innerHTML = `
        <div class="analysis-header">
            <div class="score-circle" id="atsScoreCircle" data-score="${analysis.ats_score}">
                <svg viewBox="0 0 120 120">
                    <defs>
                        <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" style="stop-color:#6C63FF"/>
                            <stop offset="100%" style="stop-color:#00D4AA"/>
                        </linearGradient>
                    </defs>
                    <circle class="circle-bg" cx="60" cy="60" r="50"/>
                    <circle class="circle-progress" cx="60" cy="60" r="50"
                        stroke-dasharray="314"
                        stroke-dashoffset="${314 - (314 * analysis.ats_score / 100)}"/>
                </svg>
                <span class="score-value">${analysis.ats_score}</span>
                <span class="score-label">ATS Score</span>
            </div>
            <div>
                <h2>Resume Analysis Complete</h2>
                <p>${analysis.summary || 'Your resume has been analyzed successfully.'}</p>
                ${analysis.mock ? '<span class="badge badge-warning">Demo Data</span>' : ''}
            </div>
        </div>

        <div class="analysis-grid">
            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">✅ Strong Skills</h3>
                </div>
                <ul class="skill-list">
                    ${(analysis.strong_skills || []).map(s => `
                        <li><span class="skill-icon" style="color:var(--success)">●</span> ${s}</li>
                    `).join('')}
                </ul>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">⚠️ Weak Areas</h3>
                </div>
                <ul class="skill-list">
                    ${(analysis.weak_skills || []).map(s => `
                        <li><span class="skill-icon" style="color:var(--warning)">●</span> ${s}</li>
                    `).join('')}
                </ul>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">🔑 Missing Keywords</h3>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:0.4rem;">
                    ${(analysis.missing_keywords || []).map(k => `
                        <span class="tag">${k}</span>
                    `).join('')}
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">📝 Grammar & Style</h3>
                </div>
                <ul class="skill-list">
                    ${(analysis.grammar_issues || []).map(g => `
                        <li><span class="skill-icon" style="color:var(--info)">●</span> ${g}</li>
                    `).join('')}
                </ul>
            </div>
        </div>

        <div class="card" style="margin-top: 1.5rem;">
            <div class="card-header">
                <h3 class="card-title">🎯 Action Plan</h3>
            </div>
            <ol style="padding-left: 1.25rem; color: var(--text-secondary);">
                ${(analysis.action_plan || []).map(a => `
                    <li style="margin-bottom: 0.5rem;">${a}</li>
                `).join('')}
            </ol>
        </div>
    `;

    initScoreCircles();
}

// ── Score Circle Animation ──────────────────────
function initScoreCircles() {
    document.querySelectorAll('.score-circle').forEach(circle => {
        const score = parseInt(circle.dataset.score) || 0;
        const progress = circle.querySelector('.circle-progress');
        const valueEl = circle.querySelector('.score-value');
        
        if (progress) {
            const circumference = 314;
            const offset = circumference - (circumference * score / 100);
            progress.style.strokeDashoffset = circumference;
            
            setTimeout(() => {
                progress.style.strokeDashoffset = offset;
            }, 300);
        }
        
        if (valueEl) {
            CareerPilot.animateCounter(valueEl, score);
        }
    });
}
