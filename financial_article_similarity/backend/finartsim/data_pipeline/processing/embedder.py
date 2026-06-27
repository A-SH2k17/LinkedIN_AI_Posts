import numpy as np
from typing import List
import torch
import torch.nn.functional as F
from torch import Tensor
from transformers import AutoTokenizer, AutoModel

def last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
    if left_padding:
        return last_hidden_states[:, -1]
    else:
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]


def embed_titles(titles_json: List,batch_size: int = 16, max_length: int = 64):
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

        return embeddings_json