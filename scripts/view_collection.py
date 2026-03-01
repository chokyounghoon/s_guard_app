import chromadb
import pandas as pd
import json

# Setup ChromaDB connection
client = chromadb.HttpClient(host="localhost", port=8001)

# Collection name
collection_name = "s_guard_knowledge"

def view_collection():
    try:
        # Get the collection
        collection = client.get_collection(name=collection_name)
        
        # Fetch all records
        results = collection.get()
        
        if not results or not results['ids']:
            print(f"Collection '{collection_name}' is empty or not found.")
            return

        # Prepare data for Pandas DataFrame
        data = []
        for i in range(len(results['ids'])):
            row = {
                "ID": results['ids'][i],
                "Content": results['documents'][i],
            }
            # Flatten metadata into the row
            if results['metadatas'][i]:
                for key, value in results['metadatas'][i].items():
                    row[f"Meta: {key}"] = value
                    
            data.append(row)

        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Configure Pandas to display all columns and wide rows
        pd.set_option('display.max_columns', None)
        pd.set_option('display.max_colwidth', 50)
        pd.set_option('display.width', 1000)

        print(f"\n✅ Total records in '{collection_name}': {len(df)}")
        print("-" * 80)
        print(df)
        print("-" * 80)
        
    except Exception as e:
        print(f"Error accessing collection: {e}")

if __name__ == "__main__":
    view_collection()
