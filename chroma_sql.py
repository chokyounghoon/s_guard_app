import chromadb

# ChromaDB 저장 경로 지정
client = chromadb.PersistentClient(path="./chroma_db") 
collection = client.get_collection(name="s_autopilot_kb") # 사용하신 컬렉션 이름

# 저장된 총 임베딩/문서 개수 
print(f"수집된 데이터 개수: {collection.count()}")
