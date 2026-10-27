# CareerPilotAI 🚀
### Your AI-Powered Career Assistant

CareerPilotAI is an AI-powered web application designed to help users improve their resumes, explore career opportunities, and prepare for their professional journey.

The project combines AI, resume intelligence, and career-focused tools in one platform.

## ✨ Features

- **AI Career Assistant** — Get career-related guidance and answers to your questions.
- **Resume Intelligence** — Analyze resume content and get useful feedback.
- **Career Profiles** — Maintain career-related information in one place.
- **Job Notifications** — Access job-related updates and notifications.
- **Problem Solving** — Explore tools and resources to improve problem-solving skills.
- **Dashboard** — Access career features from a central dashboard.
- **AI Integration** — Uses an AI provider for intelligent responses.
- **Web Interface** — A responsive interface built with HTML, CSS, and JavaScript.

*Features may depend on the current application configuration and available API services.*

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Flask | Web application and routing |
| SQLite / PostgreSQL | Database support, depending on configuration |
| HTML5 | Page structure |
| CSS3 | Styling and responsive design |
| JavaScript | Frontend interactions |
| Groq API | AI-powered responses |
| Gunicorn | Production WSGI server |
| Render | Application deployment |

## 📁 Project Structure

```text
CareerPilotAI/
├── app.py
├── backend/
│   ├── database/
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
├── scripts/
├── static/
│   ├── css/
│   ├── js/
│   └── uploads/
├── templates/
├── tests/
├── logs/
├── requirements.txt
├── Procfile
├── .gitignore
└── README.md
```

*Note: The exact structure may vary slightly depending on the current repository.*

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/anshul-94/CareerPilotAI-.git
cd CareerPilotAI-
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
```

Activate it on macOS or Linux:

```bash
source venv/bin/activate
```

On Windows:

```bash
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root if the application uses `python-dotenv`.

Add the variables required by your configuration:

```env
FLASK_SECRET_KEY=replace_with_a_secure_random_secret
DEBUG=False
ENVIRONMENT=development

GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=your_supported_model_name

USE_GROQ=True
USE_OLLAMA=False
```

Add other variables only if required by your configured services, such as Tavily or Supabase.

**Important:**
- Replace the example values with your own configuration.
- Never commit `.env` to GitHub.
- Never share API keys, passwords, or production database credentials.
- Check the application's configuration code to confirm the exact variable names and expected values.

## ▶️ Run the Application

From the directory containing `app.py`, run:

```bash
python app.py
```

If the application uses Flask's development server, open:

```text
http://127.0.0.1:5000
```

The actual port depends on your application's configuration.

For development, use the local server. For production, use a production WSGI server such as Gunicorn.

## 🧪 Run Tests

Run the test suite from the project root:

```bash
python -m unittest discover tests
```

If your virtual environment is activated, this command uses the environment's Python interpreter.

Tests help verify application behavior and reduce regressions when new features or bug fixes are introduced.

## 🌐 Deployment

CareerPilotAI is deployed using Render.

Live application:

**https://careerpilotai-33yw.onrender.com**

GitHub repository:

**https://github.com/anshul-94/CareerPilotAI-**

Typical deployment process:

1. Push the reviewed code to GitHub.
2. Connect the repository to Render.
3. Configure the build and start commands.
4. Add required environment variables in Render.
5. Deploy the latest commit.
6. Review deployment logs and test the live application.

Typical Render commands:

**Build Command**

```bash
pip install -r requirements.txt
```

**Start Command**

```bash
gunicorn app:app --workers 2 --threads 4 --timeout 120
```

Confirm that the start command matches the actual Flask application entry point.

## 🗄️ Database and Storage

The application supports database configuration based on its current implementation.

- **SQLite:** Useful for local development and small-scale testing.
- **PostgreSQL:** Suitable for a deployed application that needs a managed database.
- **Supabase Storage:** Can be used for resume files when the corresponding storage integration is configured.

Before production use, verify that the correct database URL is configured, database backups are available, and uploaded files use persistent storage.

Do not assume that local SQLite files or files stored on a temporary deployment filesystem will persist across redeployments.

## 🔐 Security

Follow these practices when running or deploying CareerPilotAI:

- Keep API keys and secret keys outside the source code.
- Never commit `.env` files or database backups.
- Use HTTPS in production.
- Disable debug mode in production.
- Validate user input and enforce authentication and authorization.
- Protect uploaded resume files and personal information.
- Use secure database credentials and appropriate access policies.
- Maintain backups before important production changes.

## 🗺️ Future Improvements

Potential improvements include:

- More advanced AI-based resume analysis.
- Personalized career recommendations.
- Better job matching and notification workflows.
- Improved resume storage and management.
- Expanded automated tests.
- PostgreSQL-backed production data management.
- Monitoring, logging, and performance improvements.
- Docker-based deployment and CI/CD automation.

## 🎯 Project Goal

The goal of CareerPilotAI is to bring useful career tools and AI assistance together in a single application, helping users organize their career information and make more informed professional decisions.

## 👨‍💻 Author

**Anshul Patidar**

Linkedin: [Anshul Patidar](https://www.linkedin.com/in/anshul-patidar-5169b8328/)
GitHub: [@anshul-94](https://github.com/anshul-94)


---

If you find this project useful, consider giving the repository a ⭐ on GitHub.

*Built with Python, Flask, and AI.*
