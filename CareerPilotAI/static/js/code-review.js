/* ============================================
   CareerPilot AI — Code Review & SQL Coach JS
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    // Code Review
    const reviewBtn = document.getElementById('reviewCodeBtn');
    if (reviewBtn) reviewBtn.addEventListener('click', reviewCode);
    
    // SQL Coach
    const sqlBtn = document.getElementById('analyzeSqlBtn');
    if (sqlBtn) sqlBtn.addEventListener('click', analyzeSql);
    
    // Project Generator
    const projectBtn = document.getElementById('generateProjectBtn');
    if (projectBtn) projectBtn.addEventListener('click', generateProject);
});

// ── Code Review ─────────────────────────────────
async function reviewCode() {
    const code = document.getElementById('codeInput')?.value || '';
    const language = document.getElementById('codeLang')?.value || 'python';
    
    if (!code.trim()) {
        CareerPilot.showNotification('Please paste some code', 'warning');
        return;
    }

    const btn = document.getElementById('reviewCodeBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner spinner-sm"></span> Reviewing...';

    const container = document.getElementById('reviewResults');
    CareerPilot.showAIProcessing(container, 'AI is reviewing your code...');

    try {
        const data = await CareerPilot.api('/code-review/analyze', {
            method: 'POST',
            body: { code, language }
        });

        CareerPilot.hideAIProcessing();
        if (data.success) {
            displayCodeReview(data.review);
        }
    } catch (error) {
        CareerPilot.hideAIProcessing();
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🔍 Review Code';
    }
}

function displayCodeReview(review) {
    const container = document.getElementById('reviewResults');
    if (!container) return;

    const bugs = review.bugs || [];
    const optimizations = review.optimizations || [];
    const suggestions = review.suggestions || [];
    const complexity = review.complexity || {};
    const quality = review.code_quality || {};

    container.innerHTML = `
        <div style="animation: fadeInUp 0.4s ease;">
            <div class="dashboard-grid" style="grid-template-columns: repeat(3, 1fr); margin-bottom: 1.5rem;">
                <div class="dash-stat ${review.score >= 70 ? 'success' : review.score >= 50 ? 'warning' : 'danger'}">
                    <div class="stat-info">
                        <div class="stat-value">${review.score || 0}</div>
                        <div class="stat-label">Quality Score</div>
                    </div>
                </div>
                <div class="dash-stat danger">
                    <div class="stat-info">
                        <div class="stat-value">${bugs.length}</div>
                        <div class="stat-label">Bugs Found</div>
                    </div>
                </div>
                <div class="dash-stat info">
                    <div class="stat-info">
                        <div class="stat-value">${review.overall_quality || 'N/A'}</div>
                        <div class="stat-label">Overall</div>
                    </div>
                </div>
            </div>

            ${bugs.length ? `
                <div class="card" style="margin-bottom: 1rem;">
                    <div class="card-header"><h3 class="card-title">🐛 Bugs Detected</h3></div>
                    ${bugs.map(b => `
                        <div style="padding: 0.75rem; margin-bottom: 0.5rem; background: rgba(255,107,107,0.1); border-radius: var(--radius-sm); border-left: 3px solid var(--${b.severity === 'High' ? 'danger' : b.severity === 'Medium' ? 'warning' : 'info'});">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                                <span style="font-weight: 600;">Line ${b.line || '?'}</span>
                                <span class="badge badge-${b.severity === 'High' ? 'danger' : b.severity === 'Medium' ? 'warning' : 'info'}">${b.severity}</span>
                            </div>
                            <p style="font-size: 0.85rem; margin: 0;">${b.description}</p>
                        </div>
                    `).join('')}
                </div>
            ` : ''}

            ${optimizations.length ? `
                <div class="card" style="margin-bottom: 1rem;">
                    <div class="card-header"><h3 class="card-title">⚡ Optimizations</h3></div>
                    <ul class="skill-list">
                        ${optimizations.map(o => `<li><span class="skill-icon" style="color:var(--accent)">●</span> ${o}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}

            <div class="card">
                <div class="card-header"><h3 class="card-title">📊 Complexity</h3></div>
                <div class="grid-3">
                    <div><strong>Time:</strong> ${complexity.time || 'N/A'}</div>
                    <div><strong>Space:</strong> ${complexity.space || 'N/A'}</div>
                    <div><strong>Cyclomatic:</strong> ${complexity.cyclomatic || 'N/A'}</div>
                </div>
            </div>
        </div>
    `;
}

// ── SQL Coach ───────────────────────────────────
async function analyzeSql() {
    const query = document.getElementById('sqlInput')?.value || '';
    
    if (!query.trim()) {
        CareerPilot.showNotification('Please enter a SQL query', 'warning');
        return;
    }

    const btn = document.getElementById('analyzeSqlBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner spinner-sm"></span> Analyzing...';

    const container = document.getElementById('sqlResults');
    CareerPilot.showAIProcessing(container, 'AI is analyzing your SQL...');

    try {
        const data = await CareerPilot.api('/sql-coach/analyze', {
            method: 'POST',
            body: { query }
        });

        CareerPilot.hideAIProcessing();
        if (data.success) {
            displaySqlAnalysis(data.analysis);
        }
    } catch (error) {
        CareerPilot.hideAIProcessing();
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🔍 Analyze SQL';
    }
}

function displaySqlAnalysis(analysis) {
    const container = document.getElementById('sqlResults');
    if (!container) return;

    container.innerHTML = `
        <div style="animation: fadeInUp 0.4s ease;">
            <div class="card" style="margin-bottom: 1rem;">
                <div class="card-header"><h3 class="card-title">📖 Explanation</h3></div>
                <p style="line-height: 1.8;">${analysis.explanation || 'No explanation available.'}</p>
            </div>
            
            ${analysis.optimized_query ? `
                <div class="card" style="margin-bottom: 1rem;">
                    <div class="card-header"><h3 class="card-title">⚡ Optimized Query</h3></div>
                    <div class="code-block"><code>${analysis.optimized_query}</code></div>
                </div>
            ` : ''}

            ${analysis.suggestions?.length ? `
                <div class="card">
                    <div class="card-header"><h3 class="card-title">💡 Suggestions</h3></div>
                    <ul class="skill-list">
                        ${analysis.suggestions.map(s => `<li><span class="skill-icon" style="color:var(--accent)">●</span> ${s}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        </div>
    `;
}

// ── Project Generator ───────────────────────────
async function generateProject() {
    const domain = document.getElementById('projectDomain')?.value || '';
    const skills = document.getElementById('projectSkills')?.value || '';
    const level = document.getElementById('projectLevel')?.value || 'beginner';

    if (!domain.trim()) {
        CareerPilot.showNotification('Please enter a domain', 'warning');
        return;
    }

    const btn = document.getElementById('generateProjectBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner spinner-sm"></span> Generating...';

    const container = document.getElementById('projectResults');
    CareerPilot.showAIProcessing(container, 'AI is generating project ideas...');

    try {
        const data = await CareerPilot.api('/projects/generate', {
            method: 'POST',
            body: { domain, skills: skills.split(',').map(s => s.trim()).filter(Boolean), experience_level: level }
        });

        CareerPilot.hideAIProcessing();
        if (data.success) {
            displayProjects(data.projects || []);
        }
    } catch (error) {
        CareerPilot.hideAIProcessing();
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🚀 Generate Projects';
    }
}

function displayProjects(projects) {
    const container = document.getElementById('projectResults');
    if (!container) return;

    container.innerHTML = projects.map((p, i) => `
        <div class="card" style="margin-bottom: 1rem; animation: fadeInUp ${0.1 + i * 0.1}s ease both;">
            <h3>${p.title || 'Project Idea'}</h3>
            <p>${p.description || ''}</p>
            ${p.tech_stack ? `
                <div style="margin: 0.75rem 0;">
                    ${p.tech_stack.map(t => `<span class="tag">${t}</span>`).join(' ')}
                </div>
            ` : ''}
            <div class="grid-2" style="margin-top: 1rem; font-size: 0.85rem;">
                <div><strong>Difficulty:</strong> ${p.difficulty || 'N/A'}</div>
                <div><strong>Timeline:</strong> ${p.timeline || 'N/A'}</div>
            </div>
            ${p.architecture ? `<div style="margin-top: 0.75rem; font-size: 0.85rem;"><strong>Architecture:</strong> ${p.architecture}</div>` : ''}
        </div>
    `).join('');
}
