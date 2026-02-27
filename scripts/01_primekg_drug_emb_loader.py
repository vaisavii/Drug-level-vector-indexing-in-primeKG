"""
PrimeKG + BioBRIDGE Drug Embedding Loader
------------------------------------------

This script loads pretrained BioBRIDGE drug embeddings
and aligns them with PrimeKG drug nodes using `node_index`.

Output:
- A clustering- or neo4j tranfer -ready DataFrame:
    node_index + embedding (512d) + metadata
- Saved locally as: drug_emb_df.pkl

This is Phase 1 of the embedding integration (drug nodes only).
"""

import pickle
import numpy as np
import pandas as pd

# CONFIGURATION
DRUG_EMB_PATH = r"BioBridge\data\embeddings\esm2b_unimo_pubmedbert\drug.pkl"
DRUG_NODES_PATH = r"BioBridge\data\Processed\\drug.csv" 

print("=" * 70)
print("PrimeKG Drug Embedding Loader")
print("=" * 70)
print("Loading BioBRIDGE pretrained drug embeddings...")
print()



# 1) Loading BioBRIDGE drug embeddings (column dict)
with open(DRUG_EMB_PATH, "rb") as f:
    obj = pickle.load(f)

    # The pickle file is stored as a dictionary of columns:
    # {
    #   "node_index": [...],
    #   "node_id": [...],
    #   "node_name": [...],
    #   "embedding": np.ndarray (N, 512)
    # }

node_index_list = obj["node_index"]              
emb_matrix = obj["embedding"]                    

print(f"Total embeddings loaded: {len(node_index_list)}")
print(f"Embedding matrix shape: {emb_matrix.shape}")
print(f"Each embedding dimension: {emb_matrix.shape[1]}")
print()



# 2) Building mapping: node_index -> embedding vector (as Python list)

print("Constructing node_index → embedding dictionary...")

emb_dict = {
    int(idx): emb_matrix[i].astype(float).tolist()
    for i, idx in enumerate(node_index_list)
}

print(f"Dictionary created with {len(emb_dict)} entries.")
print()



# 3) Load drug nodes metadata 

print("Loading PrimeKG drug node metadata...")

drug_nodes = pd.read_csv(DRUG_NODES_PATH)
drug_nodes["node_index"] = drug_nodes["node_index"].astype(int)

print(f"Total drug nodes in metadata file: {len(drug_nodes)}")
print(f"Available metadata columns: {list(drug_nodes.columns)}")
print()



# 4) Clustering table (one row per drug with embedding)

print("Aligning embeddings with PrimeKG drug nodes...")

rows = []
missing = 0

for idx in drug_nodes["node_index"].tolist():
    vec = emb_dict.get(idx)
    if vec is None:
        # Some drugs may not have embeddings (expected in practice)
        missing += 1
        continue

    rows.append({"node_index": idx, "embedding": vec})

drug_emb_df = pd.DataFrame(rows)

# Attach selected metadata columns
drug_emb_df = drug_emb_df.merge(
    drug_nodes[["node_index", "node_name", "node_source", "smiles"]],
    on="node_index",
    how="left"
)

print()
print("Alignment summary:")
print(f"  Drug nodes in PrimeKG metadata: {len(drug_nodes)}")
print(f"  Drug embeddings successfully matched: {len(drug_emb_df)}")
print(f"  Missing embeddings: {missing}")

if len(drug_emb_df) > 0:
    print(f"  Example embedding dimension: {len(drug_emb_df.iloc[0]['embedding'])}")
print()


# 5) Saving clustering table

output_path = "drug_emb_df.pkl"
drug_emb_df.to_pickle(output_path)

print(f"Clustering-ready DataFrame saved to: {output_path}")
print("This file contains:")
print("  - node_index")
print("  - embedding (512-dimensional vector)")
print("  - drug metadata (name, source, smiles)")
print()
print("=" * 70)
