import logging
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
import chromadb

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_BASE_URL = "http://localhost:11434"
CHROMA_HOST = "localhost"
CHROMA_PORT = "8001"
EMBEDDING_MODEL = "nomic-embed-text" 
COLLECTION_NAME = "s_guard_knowledge"

def test_rag_retrieval(query):
    print(f"\n[RAG 검색 테스트 - {COLLECTION_NAME}]")
    print(f"질문: '{query}'")
    print("=" * 60)
    print("1. 임베딩 엔진 및 벡터 데이터베이스 연결 중...")

    try:
        # 1. Initialize Embeddings (최신 langchain_ollama 권장 방식)
        embeddings = OllamaEmbeddings(
            base_url=OLLAMA_BASE_URL,
            model=EMBEDDING_MODEL
        )

        # 2. Connect to ChromaDB (컨테이너 외부에서 접속 시 localhost:8001)
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

        # 3. Create LangChain Chroma vector store instance (최신 langchain_chroma 권장 방식)
        vectorstore = Chroma(
            client=client,
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
        )

        # 4. Create retriever
        # search_kwargs={"k": 3} means we want to retrieve the top 3 most relevant documents
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

        print("2. 사용자 질문에 대한 의미론적(Semantic) 검색 수행 중...")
        
        # 5. Perform the retrieval
        docs = retriever.invoke(query)

        if not docs:
            print("❌ 관련 문서를 찾지 못했습니다.")
            return

        print(f"\n✅ 가장 유사도가 높은 문서 {len(docs)}건을 찾았습니다:\n")
        
        # 6. Display results
        for i, doc in enumerate(docs):
            print(f"--- [순위 {i+1} 문서] ---")
            print(f"• 내용: {doc.page_content}")
            if doc.metadata:
                print(f"• 메타데이터: {doc.metadata}")
            print("-" * 60)
            print()

    except Exception as e:
        print(f"\n❌ 검색 중 오류가 발생했습니다 (Retrieval Error): {e}")

if __name__ == "__main__":
    # Test query from user constraints
    test_query = "NCP NKS OOM 장애 해결법"
    test_rag_retrieval(test_query)
