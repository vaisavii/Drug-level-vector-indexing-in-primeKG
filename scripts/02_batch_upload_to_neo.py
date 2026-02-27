# ==================================================================
# PHASE 2: PRE-CHECK + BATCH UPLOAD to Neo4j 
# ==================================================================

from neomodel import get_config, db
import pandas as pd
import math
import os

# -----------------------------
# Neo4j CONFIG
# -----------------------------
config = get_config()
config.database_url = os.environ["NEO4J_BOLT_URL"]

LABEL = "drug"       
MATCH_PROP = "node_index"

# properties to write
EMB_PROP = "biobridge_emb" # stores the actual embedding vector
DIM_PROP = "biobridge_dim" # stores the embedding dimension
FLAG_PROP = "has_biobridge_emb" # stores boolean

# batch sizes
CHECK_BATCH = 2000
UPLOAD_BATCH = 500

# If True, we abort the upload
# This prevents partial uploads and is useful for catching label/property mismatches early.
STOP_IF_MISSING_IN_NEO4J = True  # if true, does not upload if even 1 drug is missing 


print("\n" + "=" * 70)
print("Phase 2: Pre-check mapping to Neo4j + Batch upload embeddings")
print("=" * 70)

# Loading the embeddings dataframe produced in a previous step.
drug_emb_df = pd.read_pickle("drug_emb_df.pkl")

# important: node_index is string in my neo4j database
drug_emb_df["node_index"] = drug_emb_df["node_index"].astype(str).str.strip()

ids = drug_emb_df["node_index"].tolist()


# -----------------------------
# 6) PRE-CHECK: do all node_index values exist in Neo4j?
# -----------------------------

missing_ids = []
matched_total = 0

# Cypher query
check_q = f"""
UNWIND $ids AS id
OPTIONAL MATCH (d:{LABEL} {{{MATCH_PROP}: id}})
RETURN
  collect(CASE WHEN d IS NULL THEN id ELSE null END) AS missing,
  sum(CASE WHEN d IS NULL THEN 0 ELSE 1 END) AS matched
"""

print(f"Pre-checking {len(ids)} node_index values against Neo4j label :{LABEL} ...")

for i in range(0, len(ids), CHECK_BATCH):

    # Slicing out a batch of ids for this round
    batch_ids = ids[i:i + CHECK_BATCH]

    # Running the pre-check query with parameter {"ids": batch_ids}
    res, _ = db.cypher_query(check_q, {"ids": batch_ids})

    batch_missing = [x for x in res[0][0] if x is not None]
    batch_matched = int(res[0][1])

    missing_ids.extend(batch_missing)
    matched_total += batch_matched

print("\nPre-check results:")
print(f"  Embeddings in drug_emb_df: {len(ids)}")
print(f"  Matched in Neo4j:          {matched_total}")
print(f"  Missing in Neo4j:          {len(missing_ids)}")

# If there are missing ids, print a small sample and save all missing ids to a CSV for debugging
if missing_ids:
    print(f"  Example missing node_index (first 20): {missing_ids[:20]}")
    pd.Series(missing_ids, name="missing_node_index").to_csv(
        "missing_node_index_in_neo4j.csv", index=False
    )
    print("  Saved missing ids to: missing_node_index_in_neo4j.csv")


if STOP_IF_MISSING_IN_NEO4J and missing_ids:
    raise SystemExit(
        "Stopping upload because some node_index values were not found in Neo4j. "
    )



# -----------------------------
# 7) UPLOAD: write embeddings to Neo4j in batches
# -----------------------------

# Upload cypher query
upload_q = f"""
UNWIND $rows AS row
MATCH (d:{LABEL} {{{MATCH_PROP}: row.node_index}})
SET d.{EMB_PROP} = row.embedding,
    d.{DIM_PROP} = row.dim,
    d.{FLAG_PROP} = true
"""

print("\nUploading embeddings to Neo4j...")
total = len(drug_emb_df)
updated = 0

for i in range(0, total, UPLOAD_BATCH):

    # The dataframe chunk for this transaction
    chunk = drug_emb_df.iloc[i:i + UPLOAD_BATCH]


    # Building the payload as a list of dictionaries that Cypher can consume.
    # Each dict has:
    # - node_index: the matching key (string)
    # - embedding: the embedding vector (list/np array; neomodel will pass it as a Cypher param)
    # - dim: vector dimension (computed as len(embedding))
    rows_payload = [
        {
            "node_index": str(r.node_index),
            "embedding": r.embedding,
            "dim": len(r.embedding),
        }
        for r in chunk.itertuples(index=False)
    ]

    # Execute the batch update as a single Cypher query + parameters
    db.cypher_query(upload_q, {"rows": rows_payload})

    # Update and print progress
    updated += len(rows_payload)
    print(f"  Updated {updated}/{total}")

print("\nUpload complete.")

# -----------------------------
# 8) POST-CHECK in Neo4j
# -----------------------------
# This is a sanity check that embeddings were written and flagged.
post_q = f"""
MATCH (d:{LABEL})
WHERE coalesce(d.{FLAG_PROP}, false) = true
RETURN count(d) AS n_with_embedding
"""
res, _ = db.cypher_query(post_q)
n_with = int(res[0][0])

print("\nNeo4j post-check:")
print(f"  Nodes with {FLAG_PROP}=true: {n_with}")
print("=" * 70)
