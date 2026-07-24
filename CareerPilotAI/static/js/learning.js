/* ============================================
   CareerPilot AI — Learning Roadmap JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateRoadmap');
    if (generateBtn) generateBtn.addEventListener('click', generateRoadmap);
});

async function generateRoadmap() {
    const targetRole = document.getElementById('targetRole')?.value || '';
    const currentSkills = document.getElementById('currentSkills')?.value || '';
    const experienceLevel = document.getElementById('experienceLevel')?.value || 'beginner';
    
    if (!targetRole) {
        CareerPilot.showNotification('Please enter a target role', 'warning');
        return;
    }

    const btn = document.getElementById('generateRoadmap');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner spinner-sm"></span> Generating...';

    const container = document.getElementById('roadmapResults');
    CareerPilot.showAIProcessing(container, 'AI is creating your personalized roadmap...');

    try {
        const data = await CareerPilot.api('/learning/generate', {
            method: 'POST',
            body: {
                target_role: targetRole,
                current_skills: currentSkills.split(',').map(s => s.trim()).filter(Boolean),
                experience_level: experienceLevel
            }
        });

        CareerPilot.hideAIProcessing();
        if (data.success) {
            displayRoadmap(data.roadmap);
            CareerPilot.showNotification('Roadmap generated!', 'success');
        }
    } catch (error) {
        CareerPilot.hideAIProcessing();
        CareerPilot.showNotification('Failed to generate roadmap', 'danger');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '🗺️ Generate Roadmap';
    }
}

function displayRoadmap(roadmap) {
    const container = document.getElementById('roadmapResults');
    if (!container) return;

    const weeklyPlan = roadmap.weekly_plan || [];
    const courses = roadmap.courses || [];
    const books = roadmap.books || [];
    const projects = roadmap.projects || [];
    const dailyPlan = roadmap.daily_plan || {};

    container.innerHTML = `
        <div style="animation: fadeInUp 0.5s ease;">
            <div class="card" style="margin-bottom: 1.5rem;">
                <h3>🎯 ${roadmap.target_role || 'Your'} Learning Roadmap</h3>
                <p>Estimated Duration: <strong>${roadmap.estimated_duration || '6 months'}</strong></p>
                ${roadmap.mock ? '<span class="badge badge-warning">Demo Data</span>' : ''}
            </div>

            ${Object.keys(dailyPlan).length ? `
                <div class="card" style="margin-bottom: 1.5rem;">
                    <div class="card-header"><h3 class="card-title">📅 Daily Schedule</h3></div>
                    <div class="grid-2">
                        ${Object.entries(dailyPlan).map(([time, task]) => `
                            <div style="padding: 0.75rem; background: var(--bg-card); border-radius: var(--radius-sm); border: 1px solid var(--border);">
                                <div style="font-weight: 600; color: var(--primary-light); margin-bottom: 0.25rem; text-transform: capitalize;">${time}</div>
                                <div style="font-size: 0.85rem; color: var(--text-secondary);">${task}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : ''}

            ${weeklyPlan.length ? `
                <div class="card" style="margin-bottom: 1.5rem;">
                    <div class="card-header"><h3 class="card-title">📊 Weekly Plan</h3></div>
                    ${weeklyPlan.map((w, i) => `
                        <div style="display: flex; align-items: center; gap: 1rem; padding: 0.75rem 0; border-bottom: 1px solid var(--border);">
                            <div style="width: 36px; height: 36px; border-radius: 50%; background: var(--gradient-primary); display: flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: 700; color: white; flex-shrink: 0;">${i + 1}</div>
                            <div style="flex: 1;">
                                <div style="font-weight: 600; font-size: 0.9rem;">${w.week || `Week ${i + 1}`}</div>
                                <div style="font-size: 0.85rem; color: var(--text-tertiary);">${w.focus}</div>
                            </div>
                            <span class="badge badge-primary">${w.hours || 0}h</span>
                        </div>
                    `).join('')}
                </div>
            ` : ''}

            <div class="grid-2" style="margin-bottom: 1.5rem;">
                ${courses.length ? `
                    <div class="card">
                        <div class="card-header"><h3 class="card-title">📚 Courses</h3></div>
                        ${courses.map(c => `
                            <div style="padding: 0.6rem 0; border-bottom: 1px solid var(--border);">
                                <div style="font-weight: 500; font-size: 0.9rem;">${c.name}</div>
                                <div style="font-size: 0.8rem; color: var(--text-tertiary);">${c.platform} • ${c.duration}</div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
                
                ${projects.length ? `
                    <div class="card">
                        <div class="card-header"><h3 class="card-title">🛠️ Projects</h3></div>
                        ${projects.map(p => `
                            <div style="padding: 0.6rem 0; border-bottom: 1px solid var(--border);">
                                <div style="font-weight: 500; font-size: 0.9rem;">${p.name}</div>
                                <div style="font-size: 0.8rem; color: var(--text-tertiary);">${p.difficulty} • ${p.duration}</div>
                            </div>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}
