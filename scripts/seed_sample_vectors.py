"""
Seed Sample Vectors into Qdrant (Cloud or Local/In-Memory)
Allows testing the RAG pipeline in under 60 seconds without executing Colab first.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

DEFAULT_COLLECTION = "customer_support_kb"
DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "sample_kb.json"

def get_args():
    parser = argparse.ArgumentParser(description="Seed sample support knowledge base into Qdrant.")
    parser.add_argument("--data", type=str, default=str(DEFAULT_DATA_PATH), help="Path to sample_kb.json")
    parser.add_argument("--url", type=str, default=os.getenv("QDRANT_URL", ""), help="Qdrant cluster URL")
    parser.add_argument("--api-key", type=str, default=os.getenv("QDRANT_API_KEY", ""), help="Qdrant API Key")
    parser.add_argument("--collection", type=str, default=os.getenv("QDRANT_COLLECTION", DEFAULT_COLLECTION), help="Collection name")
    parser.add_argument("--in-memory", action="store_true", help="Force in-memory local testing")
    parser.add_argument("--limit", type=int, default=100, help="Max entries to index")
    return parser.parse_args()

def main():
    args = get_args()
    print("=" * 65)
    print("🌱 Customer Support RAG Chatbot - Vector Knowledge Base Seeder")
    print("=" * 65)

    data_file = Path(args.data)
    if not data_file.exists():
        print(f"[ERROR] Sample data file not found at: {data_file}")
        sys.exit(1)

    with open(data_file, "r", encoding="utf-8") as f:
        articles = json.load(f)

    articles = articles[:args.limit]
    print(f"[*] Loaded {len(articles)} articles from {data_file.name}")

    # Check for qdrant_client
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models
    except ImportError:
        print("[!] 'qdrant-client' is not installed.")
        print("[*] Install it with: pip install qdrant-client sentence-transformers")
        print("[*] Local fallback: The backend can run in in-memory mode without cloud Qdrant.")
        return

    # Check embedding model availability
    embedder = None
    try:
        from sentence_transformers import SentenceTransformer
        print("[*] Loading local embedding model: BAAI/bge-small-en-v1.5 ...")
        embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
        dim = 384
    except Exception as e:
        print(f"[!] SentenceTransformer not available: {e}")
        print("[*] Using lightweight deterministic fallback embeddings for instant testing.")
        dim = 128

    def compute_embedding(text: str):
        if embedder is not None:
            return embedder.encode(text, normalize_embeddings=True).tolist()
        # Deterministic lightweight hash-based vector for zero-dependency local seeding
        import hashlib
        import math
        vec = [0.0] * dim
        for word in text.lower().split():
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % dim
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    # Initialize client
    if args.url and not args.in_memory:
        print(f"[*] Connecting to Qdrant Cloud at: {args.url}")
        client = QdrantClient(url=args.url, api_key=args.api_key or None)
    else:
        print("[*] Running in local in-memory Qdrant client mode (:memory:)...")
        client = QdrantClient(":memory:")

    # Create collection
    print(f"[*] Recreating collection '{args.collection}' (vector dimension: {dim}, Cosine distance)...")
    client.recreate_collection(
        collection_name=args.collection,
        vectors_config=models.VectorParams(
            size=dim,
            distance=models.Distance.COSINE
        )
    )

    # Batch upsert
    print(f"[*] Computing embeddings and upserting {len(articles)} documents...")
    start_time = time.time()
    points = []
    for doc in articles:
        text_to_embed = doc.get("text", f"{doc['brand']} {doc['category']} {doc['query']} {doc['resolution']}")
        vec = compute_embedding(text_to_embed)
        points.append(
            models.PointStruct(
                id=doc["doc_id"],
                vector=vec,
                payload={
                    "brand": doc["brand"],
                    "category": doc["category"],
                    "query": doc["query"],
                    "resolution": doc["resolution"],
                    "text": text_to_embed
                }
            )
        )

    client.upsert(
        collection_name=args.collection,
        points=points
    )
    elapsed = time.time() - start_time
    print(f"[OK] Successfully seeded {len(points)} vectors in {elapsed:.2f} seconds.")

    # Run verification test query
    test_query = "Where is my refund for a returned item?"
    print("\n" + "-" * 65)
    print(f"🔍 Running verification query: \"{test_query}\"")
    q_vec = compute_embedding(test_query)
    results = client.search(
        collection_name=args.collection,
        query_vector=q_vec,
        limit=2
    )

    for i, hit in enumerate(results, 1):
        print(f"\n  Match #{i} (Score: {hit.score:.4f}):")
        print(f"  Brand: {hit.payload.get('brand')} | Category: {hit.payload.get('category')}")
        print(f"  Issue: {hit.payload.get('query')}")
        print(f"  Resolution: {hit.payload.get('resolution')[:120]}...")
    print("\n" + "=" * 65)
    print("✅ Local knowledge base seeding test complete.")

if __name__ == "__main__":
    main()
