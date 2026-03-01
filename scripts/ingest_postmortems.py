import os
import glob
import re
import chromadb
from sentence_transformers import SentenceTransformer

# 1. 설정 및 경로 초기화
REPO_DIR = "./post-mortems"
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
COLLECTION_NAME = "sguard_postmortems"

# 마크다운 파일 탐색 (재귀적 탐색으로 변경)
md_files = glob.glob(os.path.join(REPO_DIR, "**/*.md"), recursive=True)
print(f"Total markdown files found: {len(md_files)}")

# 2. 텍스트 분할기 설정 (청킹)
def split_text(text, chunk_size=1000, overlap=200):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

# 3. ChromaDB 클라이언트 설정
chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

# 기존에 컬렉션이 있다면 초기화를 위해 삭제 (테스트용)
try:
    chroma_client.delete_collection(name=COLLECTION_NAME)
    print(f"Deleted existing collection: {COLLECTION_NAME}")
except Exception:
    pass

collection = chroma_client.create_collection(name=COLLECTION_NAME)

# 4. 임베딩 모델 로드
print("Loading Embedding Model...")
# 다국어/영어 지원 빠르고 가벼운 모델
embedding_model = SentenceTransformer('all-MiniLM-L6-v2') 

# 5. 문서 파싱 및 임베딩 처리 루프
total_chunks = 0
for file_path in md_files:
    try:
        # 파일 내용을 텍스트로 바로 로드
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            continue

        # 청크 분할
        chunks = split_text(content)
        
        if not chunks:
            continue
            
        embeddings = embedding_model.encode(chunks)
        
        # 메타데이터 생성 (파일명을 출처로 활용)
        source_name = os.path.basename(file_path)
        metadatas = [{"source": source_name, "path": file_path}] * len(chunks)
        ids = [f"{source_name}_{i}" for i in range(len(chunks))]
        
        # ChromaDB 삽입
        collection.add(
            embeddings=embeddings.tolist(),
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        total_chunks += len(chunks)
        print(f"Ingested {len(chunks)} chunks from {source_name}")
        
    except Exception as e:
        print(f"Failed to process {file_path}: {e}")

print(f"\\n✅ Successfully ingested {total_chunks} chunks into ChromaDB.")
print(f"Collection count: {collection.count()}")
