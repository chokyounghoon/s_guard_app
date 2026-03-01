import chromadb
import json

client = chromadb.HttpClient(host="localhost", port=8001)
collection = client.get_collection(name="s_guard_knowledge")

# Dummy 768-dim vector to retrieve top results structurally
results = collection.query(
    query_embeddings=[[0.1]*768],
    n_results=10
)

print(f"\n--- Raw Collection Results ---")
for i, doc in enumerate(results['documents'][0]):
    print(f"[{i+1}] {doc[:50]}... | Meta: {results['metadatas'][0][i]}")

