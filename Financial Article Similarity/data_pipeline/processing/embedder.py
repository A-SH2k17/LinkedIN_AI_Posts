import os
from dotenv import load_dotenv
import numpy as np
from typing import List
import torch
import torch.nn.functional as F
from torch import Tensor
from transformers import AutoTokenizer, AutoModel
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


def last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
    if left_padding:
        return last_hidden_states[:, -1]
    else:
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]


def embed_titles(titles_json: List, emb_path, batch_size: int = 16, max_length: int = 64):
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    titles = [t["title"].replace("_", " ").title() for t in titles_json]

    tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen3-Embedding-4B', padding_side='left')
    model = AutoModel.from_pretrained('Qwen/Qwen3-Embedding-4B', torch_dtype=torch.float16)
    model.to(device)
    model.eval()

    embeddings_json = {}

    with torch.no_grad():
        for start in range(0, len(titles), batch_size):
            batch_titles = titles[start:start + batch_size]
            batch_dict = tokenizer(
                batch_titles,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            ).to(device)

            outputs = model(**batch_dict)
            embeddings = last_token_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
            embeddings = F.normalize(embeddings, p=2, dim=1)
            final_embeddings = embeddings.detach().cpu().float().numpy()

            for title, vec in zip(batch_titles, final_embeddings):
                embeddings_json[title] = vec.tolist()

            print(f"Embedded {start + len(batch_titles)}/{len(titles)}")

    with open(emb_path, "w") as f:
        json.dump(embeddings_json, f, indent=4)

        return embeddings_json


if __name__ == "__main__":
    print("Processing...")
    with open(cnbc_json_path) as cnbc_file:
        cnbc_json = json.load(cnbc_file)
    embeddings_json = embed_titles(cnbc_json, embeddings_json_path)
    print("Done...")
    print("Adding to chroma db")
    add_to_chroma_db(cnbc_json,embeddings_json)

