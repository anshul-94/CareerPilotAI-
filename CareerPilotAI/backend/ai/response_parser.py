"""
CareerPilot AI — Response Parser
Robust parsing of raw LLM outputs (JSON or Markdown) without mock logic.
"""
import json
import re

def clean_json_string(raw_text: str) -> str:
    """Strip markdown formatting (like ```json ... ```) from LLM output."""
    text = raw_text.strip()
    # Remove markdown code blocks if present
    if text.startswith("```"):
        first_newline = text.find("\n")
        last_backticks = text.rfind("```")
        if first_newline != -1 and last_backticks != -1 and last_backticks > first_newline:
            text = text[first_newline+1:last_backticks].strip()
            
    # If the LLM returned extra conversational text before or after the JSON:
    # Find the first { or [ and the last } or ]
    start_idx = text.find("{")
    list_start = text.find("[")
    
    if start_idx == -1 and list_start != -1:
        start_idx = list_start
    elif start_idx != -1 and list_start != -1:
        start_idx = min(start_idx, list_start)
        
    end_idx = text.rfind("}")
    list_end = text.rfind("]")
    
    if end_idx == -1 and list_end != -1:
        end_idx = list_end
    elif end_idx != -1 and list_end != -1:
        end_idx = max(end_idx, list_end)
        
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx:end_idx+1]
        
    return text

def parse_json_response(raw_text: str, fallback_structure: dict = None) -> dict:
    """
    Attempt to parse a JSON response from the LLM.
    If parsing fails, returns the fallback structure or an error dict.
    """
    if not fallback_structure:
        fallback_structure = {"error": "Failed to parse AI response."}
        
    cleaned = clean_json_string(raw_text)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}\nRaw Text: {raw_text}")
        return fallback_structure

def format_markdown_to_html(text: str) -> str:
    """
    Convert basic Markdown to HTML for the frontend chat interfaces.
    """
    # Extremely basic converter for bold, italic, line breaks, code blocks
    
    # Code blocks
    text = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', text, flags=re.DOTALL)
    # Inline code
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    # Line breaks
    text = text.replace('\n', '<br>')
    
    return text
