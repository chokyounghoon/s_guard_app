import os
import argparse
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions
import uuid
from typing import List, Dict, Any
from datetime import datetime

# ==============================================================================
# S-Guard RAG: Kaggle ITSM Dataset Ingestion Script
# ==============================================================================
# Usage: python ingest_kaggle_itsm.py <path_to_csv> [--collection s_guard_knowledge]
# ==============================================================================

def map_columns(df: pd.DataFrame) -> tuple[str, str, str]:
    """
    Attempt to auto-detect common Kaggle ITSM column names.
    Returns: (id_col, desc_col, resolution_col)
    """
    cols = [c.lower() for c in df.columns]
    
    id_col = None
    desc_col = None
    res_col = None
    
    # Identify ID column
    for potential in ['number', 'incident', 'id', 'ticket']:
        matches = [c for c in cols if potential in c]
        if matches:
            id_col = df.columns[cols.index(matches[0])]
            break
            
    # Identify Description
    for potential in ['short_description', 'description', 'issue', 'subject', 'title', 'document', 'content', 'eventtemplate']:
        matches = [c for c in cols if potential in c]
        if matches:
            desc_col = df.columns[cols.index(matches[0])]
            break
            
    # Identify Resolution/Close notes
    for potential in ['resolution', 'close_notes', 'solution', 'fix', 'comments']:
        matches = [c for c in cols if potential in c]
        if matches:
            res_col = df.columns[cols.index(matches[0])]
            break
            
    return id_col, desc_col, res_col

def extract_metadata(row: pd.Series, df_columns: List[str]) -> Dict[str, Any]:
    """Extra metadata to enrich the ChromaDB record"""
    meta = {
        "source": "kaggle_itsm_dataset",
        "ingested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    cols_lower = [c.lower() for c in df_columns]
    
    # Extract priority/severity if exists
    for p_col in ['priority', 'severity', 'urgency', 'impact', 'level']:
        matches = [c for c in cols_lower if p_col in c]
        if matches:
            val = str(row[df_columns[cols_lower.index(matches[0])]])
            if val and val.lower() != 'nan':
                meta["severity"] = val
            break
            
    # Extract Category
    for c_col in ['category', 'subcategory', 'topic']:
        matches = [c for c in cols_lower if c_col in c]
        if matches:
            val = str(row[df_columns[cols_lower.index(matches[0])]])
            if val and val.lower() != 'nan':
                meta["category"] = val
            break
            
    # Extract component/system
    for s_col in ['system', 'component', 'ci', 'configuration_item']:
        matches = [c for c in cols_lower if s_col in c]
        if matches:
            val = str(row[df_columns[cols_lower.index(matches[0])]])
            if val and val.lower() != 'nan':
                meta["system"] = val
            break
            
    return meta

def ingest_data(csv_path: str, collection_name: str, host: str = "localhost", port: int = 8001, batch_size: int = 100):
    print(f"Loading dataset: {csv_path}")
    if not os.path.exists(csv_path):
        print(f"Error: File '{csv_path}' not found.")
        return

    try:
        # Load CSV (handle encoding issues commonly found in Kaggle datasets)
        try:
            df = pd.read_csv(csv_path)
        except UnicodeDecodeError:
            df = pd.read_csv(csv_path, encoding='latin1')
            
        print(f"Loaded {len(df)} rows. Discovering columns...")
        
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    id_col, desc_col, res_col = map_columns(df)
    
    print("-" * 50)
    print(f"Auto-detected mappings:")
    print(f"  Incident ID : {id_col if id_col else 'Auto-generated UUID'}")
    print(f"  Description : {desc_col if desc_col else 'NOT FOUND'}")
    print(f"  Resolution  : {res_col if res_col else 'NOT FOUND'}")
    print("-" * 50)
    
    if not desc_col:
        print("Error: Could not identify a valid description/issue column.")
        print(f"Available columns: {list(df.columns)}")
        return

    # Filter out empty descriptions
    df = df.dropna(subset=[desc_col])
    if res_col:
        df[res_col] = df[res_col].fillna("No resolution documented.")
        
    documents = []
    metadatas = []
    ids = []
    
    print("Formatting documents...")
    for idx, row in df.iterrows():
        # Build Document Text
        doc_text = f"[Troubleshooting Report - ITSM History]\n"
        
        desc_text = str(row[desc_col]).strip()
        doc_text += f"Issue/Symptom: {desc_text}\n"
        
        if res_col:
            res_text = str(row[res_col]).strip()
            doc_text += f"Resolution/Action Taken: {res_text}\n"
            
        # Build Metadata
        meta = extract_metadata(row, list(df.columns))
        
        # Build ID
        record_id = str(row[id_col]) if id_col else f"itsm_{uuid.uuid4().hex[:8]}"
        
        documents.append(doc_text)
        metadatas.append(meta)
        ids.append(str(record_id))

    print(f"Connecting to ChromaDB at {host}:{port}...")
    try:
        client = chromadb.HttpClient(host=host, port=port)
        # Verify connection
        client.heartbeat()
    except Exception as e:
        print(f"ChromaDB Connection Failed: {e}")
        print("Make sure sguard-chromadb docker container is running.")
        return

    # Setup Embedding Function (all-mpnet-base-v2 produces 768 dims)
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-mpnet-base-v2")
    
    # Get or create collection
    collection = client.get_or_create_collection(
        name=collection_name, 
        embedding_function=sentence_transformer_ef
    )
    
    total_docs = len(documents)
    print(f"Starting ingestion of {total_docs} records into '{collection_name}'...")
    
    # Process in batches to avoid overwhelming the API
    successful = 0
    for i in range(0, total_docs, batch_size):
        end_idx = min(i + batch_size, total_docs)
        batch_docs = documents[i:end_idx]
        batch_meta = metadatas[i:end_idx]
        batch_ids = ids[i:end_idx]
        
        try:
            collection.upsert(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids
            )
            successful += len(batch_ids)
            print(f"  Ingested [{end_idx}/{total_docs}] records...", end='\r')
        except Exception as e:
            print(f"\nError ingesting batch {i} to {end_idx}: {e}")
            
    print(f"\n\n✅ Ingestion Complete!")
    print(f"Successfully processed and stored {successful} records.")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Kaggle ITSM CSV tickets to ChromaDB RAG Knowledge Base")
    parser.add_argument("csv_path", help="Path to the downloaded Kaggle ITSM dataset (CSV format)")
    parser.add_argument("--collection", default="s_guard_knowledge", help="ChromaDB Collection Name")
    parser.add_argument("--host", default="localhost", help="ChromaDB Host")
    parser.add_argument("--port", type=int, default=8001, help="ChromaDB Port")
    parser.add_argument("--batch", type=int, default=500, help="Batch size for ingestion")
    
    args = parser.parse_args()
    
    ingest_data(
        csv_path=args.csv_path, 
        collection_name=args.collection,
        host=args.host,
        port=args.port,
        batch_size=args.batch
    )
