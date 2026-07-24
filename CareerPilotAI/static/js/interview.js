/* ============================================
   CareerPilot AI — Interview JavaScript
   Mock interview session management
   ============================================ */

let currentQuestions = [];
let currentAnswers = [];
let currentQuestionIndex = 0;
let interviewId = null;

document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('startInterview');
    if (startBtn) startBtn.addEventListener('click', startInterview);
});

async function startInterview() {
    const role = document.getElementById('interviewRole')?.value || 'Software Developer';
    const difficulty = document.getElementById('interviewDifficulty')?.value || 'medium';
    const experience = parseInt(document.getElementById('interviewExperience')?.value || '0');
    const type = document.getElementById('interviewType')?.value || 'technical';

    const startBtn = document.getElementById('startInterview');
    startBtn.disabled = true;
    startBtn.innerHTML = '<span class="spinner spinner-sm"></span> Generating Questions...';

    try {
        const data = await CareerPilot.api('/interview/start', {
            method: 'POST',
            body: { role, difficulty, experience_years: experience, interview_type: type }
        });

        if (data.success) {
            currentQuestions = data.questions || [];
            interviewId = data.interview_id;
            currentAnswers = new Array(currentQuestions.length).fill('');
            currentQuestionIndex = 0;
            
            showInterviewSession();
        }
    } catch (error) {
        CareerPilot.showNotification('Failed to start interview', 'danger');
    } finally {
        startBtn.disabled = false;
        startBtn.innerHTML = '🎯 Start Interview';
    }
}

function showInterviewSession() {
    const setup = document.getElementById('interviewSetup');
    const session = document.getElementById('interviewSession');
    
    if (setup) setup.style.display = 'none';
    if (session) session.style.display = 'block';

    displayQuestion(0);
}

function displayQuestion(index) {
    if (index >= currentQuestions.length) {
        submitAllAnswers();
        return;
    }

    currentQuestionIndex = index;
    const q = currentQuestions[index];
    const container = document.getElementById('questionContainer');
    
    container.innerHTML = `
        <div class="question-card" style="animation: fadeInUp 0.4s ease;">
            <div class="flex-between" style="margin-bottom: 1rem;">
                <span class="question-number">Question ${index + 1} of ${currentQuestions.length}</span>
                <div class="question-meta">
                    <span class="badge badge-${q.difficulty === 'Easy' ? 'success' : q.difficulty === 'Hard' ? 'danger' : 'warning'}">${q.difficulty || 'Medium'}</span>
                    <span class="badge badge-info">${q.category || 'General'}</span>
                </div>
            </div>
            
            <div class="progress-bar" style="margin-bottom: 1.5rem;">
                <div class="progress-fill" style="width: ${((index + 1) / currentQuestions.length) * 100}%"></div>
            </div>
            
            <p class="question-text">${q.question}</p>
            
            <div class="form-group">
                <label class="form-label">Your Answer</label>
                <textarea class="form-textarea" id="answerInput" rows="5" 
                    placeholder="Type your answer here..."
                    style="min-height: 150px;">${currentAnswers[index] || ''}</textarea>
            </div>
            
            <div class="flex-between" style="margin-top: 1rem;">
                <button class="btn btn-ghost" onclick="navigateQuestion(${index - 1})" ${index === 0 ? 'disabled' : ''}>
                    ← Previous
                </button>
                <div class="flex gap-2">
                    ${index < currentQuestions.length - 1 ? 
                        `<button class="btn btn-primary" onclick="saveAndNext(${index})">Next →</button>` :
                        `<button class="btn btn-accent" onclick="saveAndNext(${index})">🎯 Submit All</button>`
                    }
                </div>
            </div>
        </div>
    `;
}

function saveAndNext(index) {
    const answer = document.getElementById('answerInput')?.value || '';
    currentAnswers[index] = answer;
    displayQuestion(index + 1);
}

function navigateQuestion(index) {
    // Save current answer first
    const answer = document.getElementById('answerInput')?.value || '';
    currentAnswers[currentQuestionIndex] = answer;
    
    if (index >= 0 && index < currentQuestions.length) {
        displayQuestion(index);
    }
}

async function submitAllAnswers() {
    const container = document.getElementById('questionContainer');
    container.innerHTML = `
        <div class="card" style="text-align: center; padding: 3rem;">
            <div class="spinner spinner-lg" style="margin: 0 auto 1.5rem;"></div>
            <h3>AI is evaluating your answers...</h3>
            <p>This may take a moment.</p>
        </div>
    `;

    try {
        const data = await CareerPilot.api('/interview/evaluate', {
            method: 'POST',
            body: { interview_id: interviewId, answers: currentAnswers }
        });

        if (data.success) {
            displayResults(data);
        }
    } catch (error) {
        CareerPilot.showNotification('Evaluation failed', 'danger');
        container.innerHTML = '<div class="card"><p>Evaluation failed. Please try again.</p></div>';
    }
}

function displayResults(data) {
    const container = document.getElementById('questionContainer');
    
    container.innerHTML = `
        <div style="animation: fadeInUp 0.5s ease;">
            <div class="card" style="text-align: center; margin-bottom: 2rem;">
                <h2 style="margin-bottom: 1.5rem;">Interview Results</h2>
                <div class="dashboard-grid" style="grid-template-columns: repeat(4, 1fr);">
                    <div class="dash-stat primary">
                        <div class="stat-info">
                            <div class="stat-value">${data.overall_score || 0}</div>
                            <div class="stat-label">Overall</div>
                        </div>
                    </div>
                    <div class="dash-stat accent">
                        <div class="stat-info">
                            <div class="stat-value">${data.communication_score || 0}</div>
                            <div class="stat-label">Communication</div>
                        </div>
                    </div>
                    <div class="dash-stat info">
                        <div class="stat-info">
                            <div class="stat-value">${data.technical_score || 0}</div>
                            <div class="stat-label">Technical</div>
                        </div>
                    </div>
                    <div class="dash-stat warning">
                        <div class="stat-info">
                            <div class="stat-value">${data.confidence_score || 0}</div>
                            <div class="stat-label">Confidence</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">📝 Feedback</h3>
                </div>
                <p style="line-height: 1.8;">${data.feedback || 'No feedback available.'}</p>
            </div>

            <div style="text-align: center; margin-top: 2rem;">
                <button class="btn btn-primary btn-lg" onclick="location.reload()">
                    🔄 New Interview
                </button>
            </div>
        </div>
    `;
}
