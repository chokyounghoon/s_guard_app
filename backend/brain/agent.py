import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

class AIAgent:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("Warning: GOOGLE_API_KEY not found.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-flash-latest')

    async def analyze_incident(self, incident_context: str, similar_cases: list) -> str:
        prompt = f"""
        You are an expert SRE (Site Reliability Engineer) AI Assistant 'S-Guard AI'.
        
        [Current Incident]
        {incident_context}
        
        [Similar Past Cases]
        {similar_cases if similar_cases else "No similar cases found."}
        
        Based on the current incident and similar past cases(if any), provide a concise response guide.
        Structure your response as:
        1. **Root Cause Analysis (Hypothesis)**: ...
        2. **Immediate Action**: ...
        3. **Prevention**: ...
        
        Keep it professional, concise, and in Korean.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI Analysis Failed: {str(e)}"

agent = AIAgent()
