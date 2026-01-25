# Simple Mock RAG for prototype speed
# In production, this would use ChromaDB with embeddings.
# Here we return hardcoded similar cases for the demo effect to ensure reliability during the user's test.

class RAGEngine:
    def __init__(self):
        # Mock database of past incidents
        self.knowledge_base = [
            {
                "issue": "DB Connection Timeout",
                "solution": "Check Max Pool Size and slow queries."
            },
            {
                "issue": "Impending Traffic Spike",
                "solution": "Scale out WAS instances."
            }
        ]

    def search(self, query: str):
        # Determine relevant case based on keywords
        results = []
        if "임계치" in query or "초과" in query:
             results.append("- Case #01: 트래픽 급증으로 인한 임계치 초과 -> L4 스위치 로드밸런싱 확인 및 증설 필요")
        if "DB" in query or "오류" in query:
             results.append("- Case #05: DB Connection Full 발생 -> Long Running Query Kill 및 Pool 설정 증대")
             
        if not results:
            results.append("- No exact match found, suggesting general system health check.")
            
        return "\n".join(results)

rag_engine = RAGEngine()
