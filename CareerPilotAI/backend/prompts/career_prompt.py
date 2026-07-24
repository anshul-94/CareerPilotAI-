"""
CareerPilot AI — Career Coach Prompts
Reusable prompt templates for the AI Career Coach chat module.
"""


def get_career_coach_system_prompt() -> str:
    """Get the system prompt for the AI Career Coach."""
    return """You are **CareerPilot AI**, an expert AI Career Coach with deep knowledge in:
- Technology career paths and industry trends
- Resume optimization and personal branding
- Interview preparation and negotiation strategies
- Skill development roadmaps
- Salary benchmarking and compensation analysis
- Project portfolio building
- Job market analysis

**Your Personality:**
- Professional yet friendly and encouraging
- Data-driven with specific recommendations
- Proactive in suggesting next steps
- Use emojis sparingly for warmth (🎯, 🚀, 💡, ✅)

**Response Guidelines:**
- Keep responses focused and actionable (300-500 words max)
- Use bullet points and headers for readability
- Include specific examples, numbers, and timelines
- Always end with a follow-up question or next step suggestion
- When discussing salaries, provide ranges for Indian and global markets

**Important:** Never make up specific company hiring data. If asked about specific openings, suggest using the Job Finder feature."""


def get_career_chat_prompt(user_message: str, chat_history: list = None,
                           user_context: dict = None) -> list[dict]:
    """
    Build the complete prompt for a career coaching conversation.
    
    Args:
        user_message: Current user message
        chat_history: Previous messages in the session
        user_context: User's profile/resume context
        
    Returns:
        List of message dicts for the Ollama API
    """
    messages = [{"role": "system", "content": get_career_coach_system_prompt()}]
    
    # Add user context if available
    if user_context:
        context_parts = []
        if user_context.get("skills"):
            context_parts.append(f"Skills: {', '.join(user_context['skills'][:15])}")
        if user_context.get("experience"):
            context_parts.append(f"Experience: {user_context['experience']}")
        if user_context.get("education"):
            context_parts.append(f"Education: {user_context['education']}")
        if user_context.get("target_role"):
            context_parts.append(f"Target Role: {user_context['target_role']}")
        
        if context_parts:
            context_msg = "User Profile:\n" + "\n".join(context_parts)
            messages.append({"role": "system", "content": context_msg})
    
    # Add chat history (last 10 messages for context window management)
    if chat_history:
        for msg in chat_history[-10:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("message", msg.get("content", ""))
            })
    
    # Add current message
    messages.append({"role": "user", "content": user_message})
    
    return messages


def get_suggested_questions(category: str = "general") -> list[str]:
    """Get suggested questions for the career coach."""
    suggestions = {
        "general": [
            "What career path is best for a CS graduate in 2025?",
            "How do I transition from development to AI/ML?",
            "What skills should I learn to increase my salary?",
            "How do I build a strong GitHub portfolio?",
            "What are the top tech companies hiring freshers?"
        ],
        "resume": [
            "How do I improve my resume's ATS score?",
            "What should a fresher's resume include?",
            "How do I write a strong professional summary?",
            "Should I include personal projects on my resume?",
            "How long should my resume be?"
        ],
        "interview": [
            "How do I prepare for a technical interview?",
            "What are common behavioral interview questions?",
            "How should I negotiate my salary?",
            "How do I handle the 'Tell me about yourself' question?",
            "What system design concepts should I know?"
        ],
        "skills": [
            "What programming language should I learn first?",
            "Is Python enough for a career in AI?",
            "What cloud certifications are most valuable?",
            "Should I learn DevOps or Full Stack?",
            "How important is DSA for job placements?"
        ],
        "jobs": [
            "What are the highest-paying tech roles in 2025?",
            "How do I find remote jobs as a fresher?",
            "What startups are best for early career growth?",
            "How do I apply to FAANG companies?",
            "What's the job market like for AI engineers?"
        ]
    }
    return suggestions.get(category, suggestions["general"])
