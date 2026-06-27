import os
from dotenv import load_dotenv
import json
from embedder import embed_titles
import json
import chromadb

load_dotenv()
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
cnbc_json_path = os.path.join(CURRENT_DIR, "../storage/raw/CNBC/cnbc_articles_2000.json")
embeddings_json_path = os.path.join(CURRENT_DIR, "../storage/processed/cnbc_embedding.json")
CHROMA_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "../storage/chromadb"))




def add_to_chroma_db(cnbc_articles,embeddings_json):
    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for i, article in enumerate(cnbc_articles):
        normalized_title = article["title"].replace("_", " ").title()

        if normalized_title not in embeddings_json:
            print(f"Skipping (no embedding found): {normalized_title}")
            continue

        ids.append(f"doc_id_{i:04d}")
        embeddings.append(embeddings_json[normalized_title])
        documents.append(normalized_title)
        metadatas.append({
            "category": "finance",
            "url": article.get("link", ""),
        })

    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name="cnbc_articles")

    # Add in batches (Chroma has a max batch size, usually ~5000+ but good practice anyway)
    BATCH_SIZE = 500
    for start in range(0, len(ids), BATCH_SIZE):
        end = start + BATCH_SIZE
        collection.add(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
            documents=documents[start:end],
        )

    
    print(f"Successfully saved {len(ids)} embeddings to ChromaDB at: {CHROMA_PATH}")





if __name__ == "__main__":
    print("Processing...")

    with open(cnbc_json_path) as cnbc_file:
        cnbc_json = json.load(cnbc_file)
    embeddings_json = embed_titles(cnbc_json, embeddings_json_path)

    with open(embeddings_json_path, "w") as f:
        json.dump(embeddings_json, f, indent=4)

    print("Done...")
    print("Adding to chroma db")
    add_to_chroma_db(cnbc_json,embeddings_json)

