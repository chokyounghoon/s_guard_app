import chromadb
from chromadb.utils import embedding_functions

# Connect
client = chromadb.HttpClient(host="localhost", port=8001)

# Collection
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-mpnet-base-v2")
collection = client.get_collection(name="s_guard_knowledge", embedding_function=sentence_transformer_ef)

print(f"Count: {collection.count()}")
results = collection.peek(limit=1)
print(results['documents'])
