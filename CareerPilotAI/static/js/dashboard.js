/* ============================================
   CareerPilot AI — Dashboard JavaScript
   Initialize dashboard charts and counters
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    initDashboardCounters();
    initResumeScoreChart();
    initInterviewScoreChart();
    initSkillRadarChart();
    initWeeklyActivityChart();
    initApplicationsChart();
});

function initDashboardCounters() {
    document.querySelectorAll('[data-counter]').forEach(el => {
        const target = parseInt(el.dataset.counter) || 0;
        CareerPilot.animateCounter(el, target);
    });
}

function initResumeScoreChart() {
    const ctx = document.getElementById('resumeScoreChart');
    if (!ctx) return;

    const score = parseInt(ctx.dataset.score) || 0;

    ChartFactory.createDoughnutChart(
        ctx.getContext('2d'),
        ['Score', 'Remaining'],
        [score, 100 - score],
        {
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            },
            cutout: '80%'
        }
    );
}

function initInterviewScoreChart() {
    const ctx = document.getElementById('interviewScoreChart');
    if (!ctx) return;

    let labels, commScores, techScores, confScores;
    try {
        const data = JSON.parse(ctx.dataset.scores || '[]');
        labels = data.map((d, i) => `Session ${i + 1}`);
        commScores = data.map(d => d.communication_score || 0);
        techScores = data.map(d => d.technical_score || 0);
        confScores = data.map(d => d.confidence_score || 0);
    } catch {
        labels = ['Session 1', 'Session 2', 'Session 3'];
        commScores = [65, 72, 78];
        techScores = [70, 68, 82];
        confScores = [60, 75, 80];
    }

    if (!labels.length) {
        labels = ['Session 1', 'Session 2', 'Session 3'];
        commScores = [65, 72, 78];
        techScores = [70, 68, 82];
        confScores = [60, 75, 80];
    }

    ChartFactory.createLineChart(
        ctx.getContext('2d'),
        labels,
        [
            { label: 'Communication', data: commScores, color: '#6C63FF' },
            { label: 'Technical', data: techScores, color: '#00D4AA' },
            { label: 'Confidence', data: confScores, color: '#FFB347' }
        ]
    );
}

function initSkillRadarChart() {
    const ctx = document.getElementById('skillRadarChart');
    if (!ctx) return;

    ChartFactory.createRadarChart(
        ctx.getContext('2d'),
        ['Python', 'SQL', 'ML/AI', 'Web Dev', 'Cloud', 'DSA'],
        [
            {
                label: 'Your Skills',
                data: [85, 70, 75, 65, 45, 60],
                color: '#6C63FF'
            },
            {
                label: 'Industry Avg',
                data: [70, 65, 60, 70, 55, 65],
                color: '#00D4AA'
            }
        ]
    );
}

function initWeeklyActivityChart() {
    const ctx = document.getElementById('weeklyActivityChart');
    if (!ctx) return;

    ChartFactory.createBarChart(
        ctx.getContext('2d'),
        ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        [{
            label: 'Activities',
            data: [3, 5, 2, 8, 4, 6, 1],
        }]
    );
}

function initApplicationsChart() {
    const ctx = document.getElementById('applicationsChart');
    if (!ctx) return;

    ChartFactory.createDoughnutChart(
        ctx.getContext('2d'),
        ['Applied', 'Saved', 'Interviewing', 'Discovered'],
        [12, 25, 3, 45]
    );
}
