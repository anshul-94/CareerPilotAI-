"""
CareerPilot AI — Conversation Manager
Handles the flow of messages between User, Memory, AgentPlanner, and local Ollama.
"""
from backend.ai.agent_planner import AgentPlanner
from backend.ai.ollama_service import ollama
from backend.models.chat import ChatModel
from backend.prompts.career_prompt import get_career_chat_prompt

class ConversationManager:
    """Manages multi-turn conversations and routing."""
    
    @staticmethod
    def handle_message(user_id: int, message: str, session_id: str, user_context: dict = None) -> dict:
        """
        Processes an incoming chat message using the full Agent pipeline.
        """
        # 1. Store User Message in DB
        ChatModel.create(user_id, session_id, "user", message, "career_coach")
        
        # 2. Agent Planner (Decide Intent) - For now, we only log it or use it for advanced routing.
        # In a fully autonomous system, this would branch out. Here we do standard chat.
        plan = AgentPlanner.plan_action(message, user_context)
        print(f"Agent Plan: {plan}") # Logging the intent
        
        # 3. Retrieve Memory
        history = ChatModel.get_session(session_id)
        # Limit history to last 10 messages for context window
        history_msgs = [{"role": h["role"], "content": h["message"]} for h in history[-10:]]
        
        # 4. Build Prompt
        messages = get_career_chat_prompt(message, history_msgs, user_context)
        
        # 5. Call LLM
        response = ollama.chat(messages, temperature=0.7)
        
        ai_message = response.get("content", "I'm unable to reach the AI service right now.")
        
        # 6. Store AI Message in DB
        ChatModel.create(user_id, session_id, "assistant", ai_message, "career_coach")
        
        return {
            "response": ai_message,
            "session_id": session_id,
            "success": response.get("success", False)
        }
        
    @staticmethod
    def stream_message(user_id: int, message: str, session_id: str, user_context: dict = None):
        """
        Stream response back to frontend.
        """
        # 1. Store User Message
        ChatModel.create(user_id, session_id, "user", message, "career_coach")
        
        # 2. Retrieve Memory
        history = ChatModel.get_session(session_id)
        history_msgs = [{"role": h["role"], "content": h["message"]} for h in history[-10:]]
        
        # 3. Build Prompt
        messages = get_career_chat_prompt(message, history_msgs, user_context)
        
        # 4. Stream LLM
        full_response = []
        for chunk in ollama.stream_chat(messages, temperature=0.7):
            full_response.append(chunk)
            yield chunk
            
        # 5. Save complete response to DB
        complete_text = "".join(full_response)
        if complete_text:
            ChatModel.create(user_id, session_id, "assistant", complete_text, "career_coach")
