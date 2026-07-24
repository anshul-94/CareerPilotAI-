# CareerPilot AI — Career Intelligence Platform

CareerPilot AI is a comprehensive, AI-powered career intelligence platform designed to help users learn skills, build their portfolios, prepare for interviews, and land their dream jobs. It acts as a 24/7 personal career copilot.

This project is built as a complete industry-level dummy AI SaaS application for portfolio and resume purposes.

## 🚀 Features

- **Smart Resume Analyzer:** Drag-and-drop resume upload that provides ATS scoring, keyword gap analysis, and tailored action plans.
- **AI Job Matchmaker:** Finds job listings that match user skills and provides a match percentage.
- **Mock Interview Pro:** Conducts dynamic, role-specific mock interviews and evaluates communication, technical knowledge, and confidence.
- **Dynamic Learning Roadmaps:** Generates week-by-week study plans tailored to the user's target role and current skill set.
- **Code & SQL Coach:** Instant code reviews, bug detection, and SQL query optimization.
- **AI Career Coach:** A 24/7 chat interface for career advice, salary negotiation tips, and behavioral interview prep.
- **Project Generator:** Generates unique portfolio project ideas based on chosen domains and tech stacks.
- **Premium UI/UX:** Built with a custom "Dark Glassmorphism" design system, CSS animations, and Chart.js integrations.

## 🛠️ Tech Stack

- **Backend:** Python, Flask, SQLite (WAL mode enabled)
- **Frontend:** HTML5, CSS3 (Custom Design System, no Tailwind), Vanilla JavaScript
- **Libraries/Tools:** Chart.js, Particles.js, AOS (Animate on Scroll), Flask-Login, Werkzeug
- **AI Integrations (Simulated/Mocked for Demo):** Grok API, Tavily API

## 📋 Prerequisites

- Python 3.9+
- pip (Python package installer)

## ⚙️ Installation & Setup

1. **Clone the repository (or navigate to the project folder)**
   ```bash
   cd CareerPilotAI
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *(If `requirements.txt` is missing, manually install: `pip install flask flask-login werkzeug requests python-dotenv`)*

4. **Initialize the Database**
   ```bash
   python init_db.py
   ```
   *This will create the `backend/database/careerpilot.db` file and set up all the necessary tables.*

5. **Set up Environment Variables**
   The project uses a `.env` file for configuration. A sample `.env` file is included.
   ```
   FLASK_APP=app.py
   FLASK_ENV=development
   SECRET_KEY=your_super_secret_key_here
   GROK_API_KEY=your_mock_grok_key
   TAVILY_API_KEY=your_mock_tavily_key
   ```

## 🚀 Running the Application

Start the Flask development server:

```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000`.

## 📂 Project Structure

```
CareerPilotAI/
├── app.py                      # Main Flask application entry point
├── init_db.py                  # Database initialization script
├── .env                        # Environment variables
├── backend/
│   ├── ai/                     # AI clients and mock responses
│   ├── database/               # Database connection and schema
│   ├── prompts/                # System prompts for AI models
│   ├── routes/                 # Flask Blueprints (Controllers)
│   └── services/               # Business logic and AI orchestration
├── static/
│   ├── css/                    # Custom CSS Design System
│   └── js/                     # Vanilla JS Modules and Chart configs
└── templates/                  # Jinja2 HTML templates
    ├── components/             # Reusable UI components
    ├── admin/                  # Admin dashboard templates
    ├── auth/                   # Login/Register templates
    ├── chat/                   # AI Coach interface
    ├── dashboard/              # Main user dashboard
    ├── interview/              # Mock interview interface
    ├── jobs/                   # Job search and code/SQL tools
    ├── learning/               # Learning roadmap generator
    ├── profile/                # User profile and history
    └── resume/                 # Resume analyzer and builder
```

## 💡 Usage Notes

- **Authentication:** You can create a new account via the `/register` page. 
- **Admin Access:** To access the admin dashboard, you must manually set `is_admin = 1` for a user in the SQLite database, or run the app and access routes if bypassing is allowed for demo purposes.
- **AI Responses:** Currently, the system uses realistic mock responses defined in `backend/ai/mock_responses.py` to ensure the platform works flawlessly without requiring paid API keys. If you add actual keys to the `.env` file, the `GrokClient` will attempt to make real API calls.

## 🎨 Design System

The platform features a fully custom CSS architecture located in `static/css/`. It relies on CSS variables (`var(--primary)`, etc.) to maintain a consistent dark-themed, glassmorphic aesthetic inspired by top-tier AI startups. No external CSS frameworks (like Tailwind or Bootstrap) were used for the core layout, ensuring maximum control over the visual identity.

---
*Built with ❤️ as an AI Portfolio Project.*
