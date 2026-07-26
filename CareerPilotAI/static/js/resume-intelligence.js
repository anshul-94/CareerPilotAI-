/**
 * CareerPilot AI — Resume Intelligence JS
 */
'use strict';

document.addEventListener('DOMContentLoaded', () => {
    loadVersions();
    
    // If a resume is pre-rendered in window.INITIAL_RESUME, render it immediately
    if (window.INITIAL_RESUME && window.INITIAL_RESUME.content) {
        renderResume(window.INITIAL_RESUME);
    }
});

async function generateResume(isDaily = false) {
    const targetRole = document.getElementById('targetRole').value;
    const btn = document.getElementById('generateBtn');
    const overlay = document.getElementById('loadingOverlay');
    
    if (overlay) overlay.style.display = 'flex';
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '⏳ Generating...';
    }
    
    try {
        const endpoint = isDaily ? '/resume/api/intelligence/daily-optimize' : '/resume/api/intelligence/generate';
        const payload = isDaily ? {} : { target_role: targetRole, template: 'modern' };
        
        const resp = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const data = await resp.json();
        
        if (data.success) {
            renderResume(data);
            loadVersions(); // Reload timeline
        } else {
            alert('Generation failed: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        console.error(err);
        alert('Network error during generation.');
    } finally {
        if (overlay) overlay.style.display = 'none';
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '✨ Generate AI Resume';
        }
    }
}

async function loadVersions() {
    const container = document.getElementById('versionTimeline');
    if (!container) return;
    
    try {
        const resp = await fetch('/resume/api/intelligence/versions');
        const data = await resp.json();
        
        if (data.success && data.versions.length > 0) {
            container.innerHTML = data.versions.map((v, idx) => `
                <div class="version-item ${idx === 0 ? 'active' : ''}" style="cursor:pointer;" onclick='renderResume(${JSON.stringify(v).replace(/'/g, "&#39;")})'>
                    <div class="version-title">v${data.versions.length - idx}: ${esc(v.role_target)}</div>
                    <div class="version-meta">${v.version_type === 'daily_optimization' ? '🤖 Daily Optimized' : '⚡ AI Generated'}</div>
                    <div class="version-meta" style="color:#a5b4fc;">ATS: ${(v.scores && v.scores.ats) || 0}%</div>
                </div>
            `).join('');
        }
    } catch (err) {
        console.error("Failed to load versions", err);
    }
}

function renderResume(versionData) {
    if (!versionData || !versionData.content) return;
    
    const content = versionData.content;
    const scores = versionData.scores || {};
    const suggestions = versionData.suggestions || [];
    
    // 1. Update Scores
    updateScore('score-ats', scores.ats);
    updateScore('score-keyword', scores.keyword);
    updateScore('score-readability', scores.readability);
    updateScore('score-impact', scores.impact);
    
    // 2. Update Suggestions
    const suggContainer = document.getElementById('suggestionsList');
    if (suggContainer) {
        if (suggestions.length === 0) {
            suggContainer.innerHTML = '<div style="font-size:0.8rem;color:#94a3b8;">No suggestions. Resume looks great!</div>';
        } else {
            suggContainer.innerHTML = suggestions.map(s => `
                <div class="suggestion-item">
                    <span style="font-size:1.1rem;">💡</span>
                    <span>${esc(s)}</span>
                </div>
            `).join('');
        }
    }
    
    // 3. Render HTML Preview
    const preview = document.getElementById('resumePreview');
    if (!preview) return;
    
    let html = `<div class="resume-modern">`;
    
    // Header
    const name = window.USER_NAME || 'Your Name';
    const email = window.USER_EMAIL || 'email@example.com';
    const location = window.USER_LOCATION || 'City, State';
    
    html += `
        <h1>${esc(name)}</h1>
        <div class="contact-info">${esc(email)} | ${esc(location)}</div>
    `;
    
    // Summary
    if (content.professional_summary) {
        html += `
            <h2>Professional Summary</h2>
            <p style="font-size:0.95rem; line-height:1.6; color:#333;">${esc(content.professional_summary)}</p>
        `;
    }
    
    // Experience
    if (content.experience && content.experience.length > 0) {
        html += `<h2>Experience</h2>`;
        content.experience.forEach(exp => {
            html += `
                <div class="job-header">
                    <span><strong>${esc(exp.role)}</strong>, ${esc(exp.company)}</span>
                    <span style="font-size:0.9rem; color:#666;">${esc(exp.duration)}</span>
                </div>
                <ul>
                    ${(exp.bullets || []).map(b => `<li>${esc(b)}</li>`).join('')}
                </ul>
            `;
        });
    }
    
    // Projects
    if (content.projects && content.projects.length > 0) {
        html += `<h2>Projects</h2>`;
        content.projects.forEach(proj => {
            html += `
                <div class="job-header">
                    <span><strong>${esc(proj.name)}</strong></span>
                </div>
                <p style="font-size:0.9rem; color:#555; margin-bottom:0.25rem;">${esc(proj.description)}</p>
                <ul>
                    ${(proj.bullets || []).map(b => `<li>${esc(b)}</li>`).join('')}
                </ul>
            `;
        });
    }
    
    // Skills
    if (content.technical_skills && content.technical_skills.length > 0) {
        html += `
            <h2>Technical Skills</h2>
            <p style="font-size:0.95rem; color:#333;">${content.technical_skills.map(s => esc(s)).join(', ')}</p>
        `;
    }
    
    html += `</div>`;
    preview.innerHTML = html;
}

function updateScore(elementId, value) {
    const el = document.getElementById(elementId);
    if (!el) return;
    
    value = value || 0;
    el.textContent = value + '%';
    el.className = 'score-value'; // reset
    if (value >= 85) el.classList.add('high');
    else if (value >= 70) el.classList.add('mid');
    else el.classList.add('low');
}

function esc(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
