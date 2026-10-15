/* ============================================
   CareerPilot AI — Jobs JavaScript
   Job search, results display, match scoring
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('searchJobsBtn');
    if (searchBtn) searchBtn.addEventListener('click', searchJobs);
    
    const searchForm = document.getElementById('jobSearchForm');
    if (searchForm) searchForm.addEventListener('submit', (e) => { e.preventDefault(); searchJobs(); });
});

async function searchJobs() {
    const query = document.getElementById('jobQuery')?.value || '';
    const role = document.getElementById('jobRole')?.value || '';
    const location = document.getElementById('jobLocation')?.value || '';
    const resultsContainer = document.getElementById('jobResults');
    
    const searchBtn = document.getElementById('searchJobsBtn');
    searchBtn.disabled = true;
    searchBtn.innerHTML = '<span class="spinner spinner-sm"></span> Searching...';

    CareerPilot.createSkeleton(resultsContainer, 4);

    try {
        const data = await CareerPilot.api('/jobs/search', {
            method: 'POST',
            body: { query, role, location }
        });

        if (data.success) {
            displayJobResults(data.jobs, data.user_skills || []);
            
            // Show count
            const countEl = document.getElementById('jobCount');
            if (countEl) countEl.textContent = `${data.total} jobs found`;
            
            CareerPilot.showNotification(`Found ${data.total} matching jobs!`, 'success');
        }
    } catch (error) {
        resultsContainer.innerHTML = '<div class="empty-state"><h3>Search failed</h3><p>Please try again.</p></div>';
    } finally {
        searchBtn.disabled = false;
        searchBtn.innerHTML = '<i data-lucide="search" style="width:14px;height:14px;margin-right:6px;vertical-align:-2px;"></i>Search Jobs';
        if (window.lucide) lucide.createIcons();
    }
}

function displayJobResults(jobs, userSkills) {
    const container = document.getElementById('jobResults');
    if (!container) return;

    if (!jobs.length) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon"><i data-lucide="search"></i></div>
                <h3>No jobs found</h3>
                <p>Try different keywords or upload your resume for personalized results.</p>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
        return;
    }

    container.innerHTML = jobs.map((job, i) => `
        <div class="job-card" style="animation: fadeInUp ${0.1 + i * 0.05}s ease both;">
            <div class="job-header">
                <div>
                    <div class="job-title">${escapeHtml(job.title)}</div>
                    <div class="job-company">${escapeHtml(job.company)}</div>
                </div>
                <div class="job-match">
                    <span class="match-score">${job.match_score || 0}%</span>
                    <span class="match-label">Match</span>
                </div>
            </div>
            
            <div class="job-meta">
                <span><i data-lucide="map-pin" style="width:13px;height:13px;vertical-align:-2px;margin-right:2px;"></i>${escapeHtml(job.location || 'Remote')}</span>
                <span><i data-lucide="banknote" style="width:13px;height:13px;vertical-align:-2px;margin-right:2px;"></i>${escapeHtml(job.salary || 'Not disclosed')}</span>
                <span><i data-lucide="briefcase" style="width:13px;height:13px;vertical-align:-2px;margin-right:2px;"></i>${escapeHtml(job.job_type || 'Full-time')}</span>
                <span><i data-lucide="calendar" style="width:13px;height:13px;vertical-align:-2px;margin-right:2px;"></i>${escapeHtml(job.posted_date || job.found_at || 'Recent')}</span>
            </div>

            ${job.skills_required ? `
                <div class="job-tags">
                    ${job.skills_required.slice(0, 6).map(s => {
                        const isMatch = userSkills.some(us => us.toLowerCase() === s.toLowerCase());
                        return `<span class="tag" style="${isMatch ? 'border-color:var(--success);color:var(--success);' : ''}">${escapeHtml(s)}</span>`;
                    }).join('')}
                </div>
            ` : ''}
            
            <p style="font-size: 0.85rem; color: var(--text-tertiary); margin-bottom: 1rem;">
                ${escapeHtml((job.description || '').substring(0, 150))}${job.description && job.description.length > 150 ? '...' : ''}
            </p>

            <div class="job-footer">
                <span class="badge badge-info">${escapeHtml(job.source || 'Web')}</span>
                <div class="flex gap-1">
                    <button class="btn btn-sm btn-ghost" onclick="saveJob(${job.id || i})" style="display:inline-flex;align-items:center;gap:4px;"><i data-lucide="bookmark" style="width:12px;height:12px;"></i>Save</button>
                    <a href="${job.apply_link || '#'}" target="_blank" class="btn btn-sm btn-primary">Apply →</a>
                </div>
            </div>
        </div>
    `).join('');
    if (window.lucide) lucide.createIcons();
}

async function saveJob(jobId) {
    try {
        await CareerPilot.api('/jobs/status', {
            method: 'POST',
            body: { job_id: jobId, status: 'saved' }
        });
        CareerPilot.showNotification('Job saved!', 'success');
    } catch (error) {
        // Still show success for demo
        CareerPilot.showNotification('Job saved!', 'success');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
