/**
 * CareerPilot AI — AI Job Notification Agent JavaScript
 * Handles: agent triggering, job card rendering, filter tabs,
 *          chart rendering, status updates, insights, and live UI updates.
 */

'use strict';

// ─── State ────────────────────────────────────────────────
let allNotifications   = [];
let currentFilter      = 'all';
let chartsInitialized  = false;
let chartInstances     = {};

// ─── Init ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Load missing skills
    if (document.getElementById('missingSkillsList')) {
        loadMissingSkills();
    }
    // Load insights from API
    if (document.getElementById('insightsList')) {
        loadInsights();
    }
    // Load charts
    if (document.getElementById('funnelChart')) {
        loadCharts();
    }
    // Collect initial notifications from DOM
    collectNotificationsFromDOM();
});

// ─── Collect Jobs from DOM ─────────────────────────────────
function collectNotificationsFromDOM() {
    const cards = document.querySelectorAll('.notif-card[data-match]');
    cards.forEach(card => {
        allNotifications.push({
            id:         card.id.replace('notif-', ''),
            match:      parseInt(card.dataset.match || 0),
            shortlist:  parseInt(card.dataset.shortlist || 0),
            remote:     card.dataset.remote === '1',
            urgency:    card.dataset.urgency || 'normal',
            status:     card.dataset.status || 'new',
            category:   card.dataset.category || 'medium_match',
            el:         card
        });
    });
}

// ─── Filter Tabs ───────────────────────────────────────────
function filterJobs(filter) {
    currentFilter = filter;

    // Update tab active state
    document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
    const activeTab = document.getElementById('tab-' + filter);
    if (activeTab) activeTab.classList.add('active');

    // Filter cards
    const cards = document.querySelectorAll('.notif-card[data-match]');
    let shown = 0;
    cards.forEach(card => {
        let visible = false;
        const match     = parseInt(card.dataset.match || 0);
        const isRemote  = card.dataset.remote === '1';
        const urgency   = card.dataset.urgency || 'normal';
        const status    = card.dataset.status || 'new';

        switch(filter) {
            case 'all':        visible = status !== 'hidden'; break;
            case 'high_match': visible = match >= 80 && status !== 'hidden'; break;
            case 'medium_match': visible = match >= 60 && match < 80 && status !== 'hidden'; break;
            case 'low_match':  visible = match < 60 && status !== 'hidden'; break;
            case 'urgent':     visible = urgency === 'urgent' && status !== 'hidden'; break;
            case 'remote':     visible = isRemote && status !== 'hidden'; break;
            case 'saved':      visible = status === 'saved'; break;
            default:           visible = status !== 'hidden';
        }

        card.style.display = visible ? '' : 'none';
        if (visible) shown++;
    });

    // Show empty state if no results
    const grid = document.getElementById('notifGrid');
    let emptyEl = grid ? grid.querySelector('.notif-empty-filter') : null;
    if (shown === 0 && grid) {
        if (!emptyEl) {
            emptyEl = document.createElement('div');
            emptyEl.className = 'agent-empty notif-empty-filter';
            emptyEl.style.gridColumn = '1 / -1';
            emptyEl.innerHTML = `
                <div class="agent-empty-icon">🔎</div>
                <h3>No ${filter.replace('_', ' ')} jobs</h3>
                <p>Try running the AI Agent again or switch to another filter.</p>
            `;
            grid.appendChild(emptyEl);
        }
        emptyEl.style.display = '';
    } else if (emptyEl) {
        emptyEl.style.display = 'none';
    }
}

// ─── Run AI Agent ──────────────────────────────────────────
async function runAgent() {
    const btn     = document.getElementById('runAgentBtn');
    const spinner = document.getElementById('runSpinner');
    const btnText = document.getElementById('runBtnText');
    const overlay = document.getElementById('agentOverlay');

    if (!btn) return;

    // Show UI
    btn.disabled   = true;
    if (spinner) spinner.style.display = 'block';
    if (btnText) btnText.textContent   = 'AI Agent Running...';
    if (overlay) overlay.style.display = 'flex';

    // Animate steps
    const steps = [1,2,3,4,5];
    const delays = [0, 2500, 5000, 8000, 11000];
    steps.forEach((s, i) => {
        setTimeout(() => animateStep(s), delays[i]);
    });

    try {
        const resp = await fetch('/notifications/api/run-agent', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({fresh: true})
        });
        const data = await resp.json();

        if (data.success) {
            // Update briefing
            updateDailyBriefing(data.daily_summary, data);
            updateStats(data.stats, data.jobs_searched, data.jobs_matched);
            showSuccess(`✅ AI Agent found ${data.jobs_matched} job matches!`);

            // Reload notifications
            await loadNotifications();
            await loadCharts();
            await loadInsights();
            await loadMissingSkills();
        } else {
            showError('Agent error: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        console.error('Agent run error:', err);
        showError('Failed to reach the AI Agent. Check your connection.');
    } finally {
        // Reset UI
        if (overlay)  overlay.style.display = 'none';
        btn.disabled = false;
        if (spinner) spinner.style.display = 'none';
        if (btnText) btnText.textContent   = '⚡ Run AI Agent';
    }
}

function animateStep(stepNum) {
    for (let i = 1; i <= 5; i++) {
        const stepEl = document.getElementById('step' + i);
        const indEl  = stepEl ? stepEl.querySelector('.step-indicator') : null;
        if (!stepEl || !indEl) continue;

        if (i < stepNum) {
            stepEl.classList.remove('active');
            stepEl.classList.add('done');
            indEl.classList.remove('active');
            indEl.classList.add('done');
            indEl.textContent = '✓';
        } else if (i === stepNum) {
            stepEl.classList.add('active');
            indEl.classList.add('active');
        } else {
            stepEl.classList.remove('active', 'done');
            indEl.classList.remove('active', 'done');
        }
    }
}

// ─── Load Notifications ────────────────────────────────────
async function loadNotifications(filter) {
    try {
        const url = filter
            ? `/notifications/api/notifications?category=${filter}`
            : '/notifications/api/notifications';
        const resp = await fetch(url);
        const data = await resp.json();

        if (data.success && data.jobs) {
            renderNotificationCards(data.jobs);
        }
    } catch(err) {
        console.error('Load notifications error:', err);
    }
}

function renderNotificationCards(jobs) {
    const grid = document.getElementById('notifGrid');
    if (!grid) return;

    if (!jobs.length) {
        grid.innerHTML = `
            <div class="agent-empty">
                <div class="agent-empty-icon">🤖</div>
                <h3>No matches found</h3>
                <p>Try uploading your resume and running the AI Agent again.</p>
            </div>`;
        return;
    }

    // Reset allNotifications
    allNotifications = [];

    const cards = jobs.map(job => buildJobCard(job)).join('');
    grid.innerHTML = cards;

    // Collect for filtering
    jobs.forEach(job => {
        allNotifications.push({
            id:       job.id,
            match:    job.resume_match || 0,
            shortlist:job.shortlist_probability || 0,
            remote:   job.is_remote,
            urgency:  job.urgency || 'normal',
            status:   job.status || 'new',
            category: job.category || 'medium_match',
        });
    });

    // Update tab counts
    updateTabCounts(jobs);

    // Re-apply current filter
    if (currentFilter !== 'all') {
        filterJobs(currentFilter);
    }

    // Animate bars
    requestAnimationFrame(() => animateScoreBars());
}

function buildJobCard(job) {
    const match     = job.resume_match || 0;
    const shortlist = job.shortlist_probability || 0;
    const interview = job.interview_probability || 0;
    const ats       = job.ats_score || 0;

    const matchClass  = match >= 80 ? 'high-match' : match >= 60 ? 'medium-match' : 'low-match';
    const scoreColor  = match >= 80 ? '#22c55e' : match >= 60 ? '#f59e0b' : '#64748b';
    const shortClass  = shortlist >= 80 ? 'high' : shortlist >= 60 ? 'medium' : 'low';

    const logoUrl = job.company_logo ||
        `https://ui-avatars.com/api/?name=${encodeURIComponent(job.company.slice(0,2))}&background=4f46e5&color=fff&size=64`;

    const matchingSkills = (job.matching_skills || []).slice(0,4).map(s =>
        `<span class="skill-tag matching">✓ ${esc(s)}</span>`).join('');
    const missingSkills = (job.missing_skills || []).slice(0,3).map(s =>
        `<span class="skill-tag missing">✗ ${esc(s)}</span>`).join('');

    const remoteBadge  = job.is_remote ? `<span class="notif-meta-chip remote">🌍 Remote</span>` : '';
    const urgentBadge  = job.urgency === 'urgent'
        ? `<span class="notif-meta-chip urgent">⚡ Urgent</span>` : '';
    const freshBadge   = job.freshness === 'today'
        ? `<span class="notif-meta-chip" style="background:rgba(34,197,94,0.12);color:#86efac;">🔥 Today</span>` : '';

    return `
    <div class="notif-card ${matchClass}" id="notif-${job.id}"
         data-match="${match}" data-shortlist="${shortlist}"
         data-remote="${job.is_remote ? 1 : 0}" data-urgency="${job.urgency || 'normal'}"
         data-status="${job.status || 'new'}" data-category="${job.category || 'medium_match'}">
        <div class="notif-card-header">
            <div class="company-logo-wrap">
                <img class="company-logo" src="${logoUrl}" alt="${esc(job.company)}"
                     onerror="this.src='${logoUrl}'">
            </div>
            <div class="notif-card-title-block">
                <div class="notif-job-title">${esc(job.title)}</div>
                <div class="notif-company">${esc(job.company)}</div>
            </div>
            <div class="notif-card-scores">
                <div class="score-circle"
                     style="--score-pct:${match};--score-color:${scoreColor};">
                    <span class="score-circle-value">${match}%</span>
                </div>
                <div class="score-circle-label">Match</div>
            </div>
        </div>

        <div class="shortlist-badge ${shortClass}">
            🎯 Shortlist: ${shortlist}% &nbsp;·&nbsp; 📞 Interview: ${interview}%
        </div>

        <div class="score-bars">
            <div class="score-bar-item">
                <div class="score-bar-label">ATS Score</div>
                <div class="score-bar-track">
                    <div class="score-bar-fill ats" style="width:0%" data-target="${ats}"></div>
                </div>
                <div class="score-bar-value">${ats}%</div>
            </div>
            <div class="score-bar-item">
                <div class="score-bar-label">Shortlist</div>
                <div class="score-bar-track">
                    <div class="score-bar-fill shortlist" style="width:0%" data-target="${shortlist}"></div>
                </div>
                <div class="score-bar-value">${shortlist}%</div>
            </div>
            <div class="score-bar-item">
                <div class="score-bar-label">Interview</div>
                <div class="score-bar-track">
                    <div class="score-bar-fill interview" style="width:0%" data-target="${interview}"></div>
                </div>
                <div class="score-bar-value">${interview}%</div>
            </div>
        </div>

        <div class="notif-meta">
            <span class="notif-meta-chip">📍 ${esc(job.location || 'Remote')}</span>
            <span class="notif-meta-chip">💰 ${esc(job.salary_estimate || job.salary_raw || 'Not disclosed')}</span>
            <span class="notif-meta-chip">💼 ${esc(job.job_type || 'Full-time')}</span>
            ${remoteBadge}${urgentBadge}${freshBadge}
        </div>

        ${job.ai_summary ? `<div class="notif-ai-summary">🤖 ${esc(job.ai_summary)}</div>` : ''}

        <div class="notif-skills">
            ${matchingSkills}${missingSkills}
        </div>

        <div class="notif-card-footer">
            <span class="notif-source-badge">${esc(job.source || 'Web')}</span>
            <div class="notif-card-actions">
                <button class="btn-notif btn-notif-save ${job.status === 'saved' ? 'active' : ''}"
                        onclick="updateNotifStatus(${job.id}, 'save', this)">
                    ${job.status === 'saved' ? '💾 Saved' : '💾 Save'}
                </button>
                <button class="btn-notif btn-notif-hide"
                        onclick="updateNotifStatus(${job.id}, 'hide', this)">✕</button>
                <a href="${job.apply_link || '#'}" target="_blank"
                   class="btn-notif btn-notif-apply"
                   onclick="updateNotifStatus(${job.id}, 'apply', null)">Apply →</a>
            </div>
        </div>
    </div>`;
}

function animateScoreBars() {
    document.querySelectorAll('.score-bar-fill[data-target]').forEach(bar => {
        const target = bar.dataset.target || 0;
        setTimeout(() => { bar.style.width = target + '%'; }, 100);
    });
}

// ─── Status Updates ────────────────────────────────────────
async function updateNotifStatus(jobId, action, btnEl) {
    try {
        const resp = await fetch('/notifications/api/update-status', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({job_id: jobId, action})
        });
        const data = await resp.json();

        if (data.success) {
            const card = document.getElementById('notif-' + jobId);
            if (!card) return;

            if (action === 'hide') {
                card.style.transition = 'all 0.4s ease';
                card.style.opacity    = '0';
                card.style.transform  = 'scale(0.95)';
                setTimeout(() => card.remove(), 400);
            } else if (action === 'save' && btnEl) {
                card.dataset.status = 'saved';
                btnEl.innerHTML     = '💾 Saved';
                btnEl.classList.add('active');
            } else if (action === 'apply') {
                card.dataset.status = 'applied';
            }
        }
    } catch(err) {
        console.error('Status update error:', err);
    }
}

// ─── Stats Update ─────────────────────────────────────────
function updateStats(stats, jobsSearched, jobsMatched) {
    if (!stats) return;
    setElText('statTotal',     stats.total || 0);
    setElText('statHighMatch', stats.high_match || 0);
    setElText('statShortlist', stats.high_shortlist || 0);
    setElText('statAvgMatch',  Math.round(stats.avg_match || 0) + '%');
}

function updateTabCounts(jobs) {
    const counts = {
        all:          jobs.filter(j => j.status !== 'hidden').length,
        high_match:   jobs.filter(j => (j.resume_match||0) >= 80 && j.status !== 'hidden').length,
        medium_match: jobs.filter(j => (j.resume_match||0) >= 60 && (j.resume_match||0) < 80 && j.status !== 'hidden').length,
        low_match:    jobs.filter(j => (j.resume_match||0) < 60 && j.status !== 'hidden').length,
        urgent:       jobs.filter(j => j.urgency === 'urgent' && j.status !== 'hidden').length,
        remote:       jobs.filter(j => j.is_remote && j.status !== 'hidden').length,
    };
    Object.entries(counts).forEach(([key, val]) => {
        const tab = document.getElementById('tab-' + key);
        if (tab) {
            const countEl = tab.querySelector('.tab-count');
            if (countEl) countEl.textContent = val;
        }
    });
}

// ─── Daily Briefing ───────────────────────────────────────
function updateDailyBriefing(summary, runData) {
    if (!summary) return;
    setElText('briefingHeadline', summary.headline || 'AI Recruiter Briefing');
    setElText('briefingBody', summary.summary || '');
    setElText('briefingInsightText', summary.top_insight || '');
    setElText('briefingActionText', summary.action_item || '');
    if (summary.unlock_tip) {
        setElText('unlockTip', `📚 Learn ${summary.unlock_tip} to unlock more job opportunities.`);
    }
}

// ─── Load AI Insights ─────────────────────────────────────
async function loadInsights() {
    try {
        const resp = await fetch('/notifications/api/insights');
        const data = await resp.json();
        if (data.success && data.insights) {
            renderInsights(data.insights);
        }
    } catch(err) {
        console.error('Load insights error:', err);
    }
}

function renderInsights(insights) {
    const list = document.getElementById('insightsList');
    if (!list || !insights.length) return;
    list.innerHTML = insights.map(item => `
        <div class="insight-item">
            <div class="insight-icon">${item.icon || '💡'}</div>
            <div class="insight-text">${esc(item.text || '')}</div>
        </div>`).join('');
}

// ─── Load Missing Skills ───────────────────────────────────
async function loadMissingSkills() {
    const el = document.getElementById('missingSkillsList');
    if (!el) return;
    try {
        const resp = await fetch('/notifications/api/missing-skills');
        const data = await resp.json();
        if (data.success && data.missing_skills.length) {
            renderMissingSkills(data.missing_skills);
        } else {
            el.innerHTML = '<p style="color:#94a3b8;font-size:0.82rem;">No data yet. Run the AI Agent first.</p>';
        }
    } catch(err) {
        el.innerHTML = '<p style="color:#94a3b8;font-size:0.82rem;">Could not load skills.</p>';
    }
}

function renderMissingSkills(skills) {
    const el = document.getElementById('missingSkillsList');
    if (!el) return;
    el.innerHTML = skills.slice(0, 8).map(s => `
        <div style="display:flex;align-items:center;justify-content:space-between;
                    margin-bottom:0.5rem;padding:0.4rem 0.5rem;
                    background:rgba(239,68,68,0.07);border-radius:8px;">
            <span style="font-size:0.82rem;color:#fca5a5;font-weight:600;">✗ ${esc(s.skill)}</span>
            <span style="font-size:0.72rem;color:#94a3b8;">${s.job_count} jobs</span>
        </div>`).join('');
}

// ─── Charts ────────────────────────────────────────────────
async function loadCharts() {
    try {
        const resp = await fetch('/notifications/api/chart-data');
        const data = await resp.json();
        if (data.success && data.charts) {
            renderAllCharts(data.charts);
        }
    } catch(err) {
        console.error('Load chart data error:', err);
        renderFallbackCharts();
    }
}

function renderAllCharts(charts) {
    renderFunnelChart(charts.funnel);
    renderMatchDistChart(charts.match_dist);
    renderCompanyChart(charts.company_dist);
    renderSkillsChart(charts.skills_heatmap);
    renderTrendChart(charts.hiring_trend);
    renderSalaryChart(charts.salary_dist);
}

function getChartDefaults() {
    return {
        color:      '#a5b4fc',
        gridColor:  'rgba(255,255,255,0.05)',
        tickColor:  '#64748b',
        gradStart:  'rgba(99,102,241,0.8)',
        gradEnd:    'rgba(99,102,241,0.05)',
        fontFamily: "'Inter', sans-serif",
    };
}

function makeGradient(ctx, color1, color2) {
    const g = ctx.createLinearGradient(0, 0, 0, 300);
    g.addColorStop(0, color1);
    g.addColorStop(1, color2);
    return g;
}

function destroyChart(id) {
    if (chartInstances[id]) {
        chartInstances[id].destroy();
        delete chartInstances[id];
    }
}

function renderFunnelChart(data) {
    const canvas = document.getElementById('funnelChart');
    if (!canvas || !data) return;
    destroyChart('funnel');
    const ctx = canvas.getContext('2d');
    const d = getChartDefaults();
    chartInstances['funnel'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Jobs',
                data: data.data || [],
                backgroundColor: ['rgba(99,102,241,0.8)', 'rgba(34,197,94,0.8)', 'rgba(56,189,248,0.8)', 'rgba(245,158,11,0.8)'],
                borderRadius: 8,
            }]
        },
        options: chartOptions(d, 'Application Funnel', false)
    });
}

function renderMatchDistChart(data) {
    const canvas = document.getElementById('matchDistChart');
    if (!canvas || !data) return;
    destroyChart('matchDist');
    const ctx = canvas.getContext('2d');
    const d = getChartDefaults();
    chartInstances['matchDist'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels || [],
            datasets: [{
                data: data.data || [],
                backgroundColor: [
                    'rgba(34,197,94,0.8)', 'rgba(74,222,128,0.8)',
                    'rgba(99,102,241,0.8)', 'rgba(245,158,11,0.8)',
                    'rgba(249,115,22,0.8)', 'rgba(100,116,139,0.5)'
                ],
                borderWidth: 2,
                borderColor: 'rgba(255,255,255,0.05)',
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { labels: { color: d.color, font: { family: d.fontFamily, size: 11 } } }
            }
        }
    });
}

function renderCompanyChart(data) {
    const canvas = document.getElementById('companyChart');
    if (!canvas || !data) return;
    destroyChart('company');
    const ctx = canvas.getContext('2d');
    const d = getChartDefaults();
    chartInstances['company'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Job Count',
                data: data.data || [],
                backgroundColor: makeGradient(ctx, 'rgba(139,92,246,0.8)', 'rgba(99,102,241,0.3)'),
                borderRadius: 6,
            }]
        },
        options: { ...chartOptions(d, '', false), indexAxis: 'y' }
    });
}

function renderSkillsChart(data) {
    const canvas = document.getElementById('skillsChart');
    if (!canvas || !data) return;
    destroyChart('skills');
    const ctx = canvas.getContext('2d');
    const d = getChartDefaults();
    chartInstances['skills'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Jobs requiring this skill',
                data: data.data || [],
                backgroundColor: makeGradient(ctx, 'rgba(239,68,68,0.8)', 'rgba(239,68,68,0.2)'),
                borderRadius: 6,
            }]
        },
        options: chartOptions(d, '', false)
    });
}

function renderTrendChart(data) {
    const canvas = document.getElementById('trendChart');
    if (!canvas || !data) return;
    destroyChart('trend');
    const ctx = canvas.getContext('2d');
    const d = getChartDefaults();
    chartInstances['trend'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels || [],
            datasets: [
                {
                    label: 'New Jobs',
                    data: data.new_jobs || [],
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99,102,241,0.1)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#6366f1',
                    pointRadius: 4,
                },
                {
                    label: 'Matched',
                    data: data.matched || [],
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34,197,94,0.1)',
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#22c55e',
                    pointRadius: 4,
                }
            ]
        },
        options: chartOptions(d, 'Hiring Trend', true)
    });
}

function renderSalaryChart(data) {
    const canvas = document.getElementById('salaryChart');
    if (!canvas || !data) return;
    destroyChart('salary');
    const ctx = canvas.getContext('2d');
    const d = getChartDefaults();
    chartInstances['salary'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels || [],
            datasets: [{
                label: 'Jobs',
                data: data.data || [],
                backgroundColor: [
                    'rgba(100,116,139,0.6)',
                    'rgba(99,102,241,0.7)',
                    'rgba(139,92,246,0.8)',
                    'rgba(167,139,250,0.8)',
                    'rgba(196,181,253,0.8)',
                ],
                borderRadius: 8,
            }]
        },
        options: chartOptions(d, 'Salary Distribution', false)
    });
}

function renderFallbackCharts() {
    // Renders demo charts when API not available
    renderFunnelChart({ labels: ['Analyzed','High Match','Saved','Applied'], data: [42, 18, 5, 2] });
    renderMatchDistChart({ labels: ['90-100','80-89','70-79','60-69','50-59','< 50'], data: [4,9,12,8,5,4] });
    renderCompanyChart({ labels: ['Razorpay','PhonePe','Flipkart','Google','CRED','Meesho','Swiggy','Zomato'], data: [3,2,2,2,1,1,1,1] });
    renderSkillsChart({ labels: ['Docker','AWS','Kubernetes','Go','CUDA','React','Redis','CI/CD'], data: [8,7,6,5,4,3,3,2] });
    renderTrendChart({ labels: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'], new_jobs: [42,65,53,78,91,34,22], matched: [18,28,21,35,42,14,9] });
    renderSalaryChart({ labels: ['< 5 LPA','5-10 LPA','10-20 LPA','20-30 LPA','> 30 LPA'], data: [2,8,12,6,4] });
}

function chartOptions(d, title, hasLegend) {
    return {
        responsive: true,
        plugins: {
            legend: {
                display: hasLegend,
                labels: { color: d.color, font: { family: d.fontFamily, size: 11 } }
            },
            title: { display: false }
        },
        scales: {
            x: {
                ticks: { color: d.tickColor, font: { family: d.fontFamily, size: 10 } },
                grid: { color: d.gridColor }
            },
            y: {
                ticks: { color: d.tickColor, font: { family: d.fontFamily, size: 10 } },
                grid: { color: d.gridColor }
            }
        }
    };
}

// ─── Helpers ───────────────────────────────────────────────
function esc(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;');
}

function setElText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function refreshPage() {
    window.location.reload();
}

function viewProfile() {
    window.location.href = '/notifications/api/profile';
}

function showSuccess(msg) {
    showToast(msg, 'success');
}

function showError(msg) {
    showToast(msg, 'error');
}

function showToast(msg, type) {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position:fixed;bottom:24px;right:24px;z-index:99999;
        background:${type === 'success' ? 'rgba(34,197,94,0.15)' : 'rgba(239,68,68,0.15)'};
        border:1px solid ${type === 'success' ? 'rgba(34,197,94,0.4)' : 'rgba(239,68,68,0.4)'};
        color:${type === 'success' ? '#86efac' : '#fca5a5'};
        border-radius:14px;padding:1rem 1.5rem;
        font-size:0.9rem;font-weight:600;
        backdrop-filter:blur(12px);
        max-width:360px;
        animation:slideInRight 0.3s ease;
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Add keyframes if not already present
if (!document.getElementById('toastStyles')) {
    const style = document.createElement('style');
    style.id = 'toastStyles';
    style.textContent = `
        @keyframes slideInRight {
            from { transform: translateX(100px); opacity: 0; }
            to   { transform: translateX(0); opacity: 1; }
        }
        @keyframes fadeOut {
            to { opacity: 0; transform: translateY(10px); }
        }
    `;
    document.head.appendChild(style);
}

// Auto-animate score bars on page load
window.addEventListener('load', () => {
    setTimeout(() => animateScoreBars(), 500);
    setTimeout(() => {
        if (!chartsInitialized && document.getElementById('funnelChart')) {
            chartsInitialized = true;
            renderFallbackCharts();
            loadCharts(); // override with real data
        }
    }, 800);
});
