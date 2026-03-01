import chromadb
from sentence_transformers import SentenceTransformer

# 1. ChromaDB 클라이언트 연결
chroma_client = chromadb.HttpClient(host="localhost", port=8001)

# 2. 저장된 컬렉션 선택
collection = chroma_client.get_collection(name="sguard_postmortems")

# 총 몇 개의 문서 단락(청크)이 저장되어 있는지 출력
print(f"Total documents in collection: {collection.count()}\\n")

# 3. 데이터 샘플 직접 가져오기 (전체 데이터에서 최대 2개만)
print("--- [ 1. 샘플 데이터 확인 (Sample Data) ] ---")
sample_data = collection.peek(limit=2)

for i in range(len(sample_data['ids'])):
    print(f"ID: {sample_data['ids'][i]}")
    print(f"메타데이터(출처): {sample_data['metadatas'][i]}")
    print(f"본문 미리보기: {sample_data['documents'][i][:150]}...\\n")


# 4. RAG 시 사용할 유사도 검색(Similarity Search) 테스트
print("--- [ 2. 벡터 유사도 검색 테스트 (Similarity Search) ] ---")

# 검색을 위한 임베딩 모델 (적재할 때 쓴 모델과 동일해야 함)
# 임베딩 모델 로드 시 로컬 경고 임시 회피를 위해 조용히 로드
embedding_model = SentenceTransformer('all-MiniLM-L6-v2') 

# 내가 찾고 싶은 장애 관련 키워드
query_text = "aws s3 outage database failover"
print(f"검색어(Query): '{query_text}'")

# 검색 텍스트를 벡터로 변환 (임베딩)
query_embedding = embedding_model.encode([query_text])

# DB에 쿼리 (가장 유사한 문서 3개 반환)
results = collection.query(
    query_embeddings=query_embedding.tolist(),
    n_results=3
)

for i, doc in enumerate(results['documents'][0]):
    print(f"\\n[ 매칭 결과 {i+1} : 유사도 점수 {results['distances'][0][i]:.4f} ]")
    print(f"출처: {results['metadatas'][0][i]['source']}")
    print(f"미리보기: {doc[:300]}...")
