# Drug-Level Vector Indexing in PrimeKG (Neo4j)
**PrimeKG × BioBRIDGE Embedding Integration**

This project integrates pretrained 512-dimensional BioBRIDGE drug embeddings into the [PrimeKG biomedical knowledge graph](https://github.com/mims-harvard/PrimeKG) and enables vector-based similarity search directly within the [Neo4j graph database](https://neo4j.com/docs/getting-started/whats-neo4j/).

The current implementation focuses on **drug nodes only**.

The goal is to combine:

- **Biomedical knowledge graph** with
- **Learned semantic representations** capturing functional and contextual similarity between drugs

By attaching embeddings directly to graph nodes and indexing them using Neo4j’s native vector index (cosine similarity), the system enables hybrid graph–vector workflows where similarity retrieval can be combined with Cypher-based graph traversal.

This work was conducted as part of my internship at the Institute of Biomedicine, University of Eastern Finland.

---

## Why this matters

Knowledge graphs encode explicit biological relationships, while embeddings capture graded functional similarity in high-dimensional space.

Integrating embeddings directly into Neo4j enables:

- Retrieval of pharmacologically similar drugs via vector search  
- Joint exploration of similarity and biological topology  
Because vector search is integrated into Cypher, similarity queries can be combined directly with graph traversal without moving data between systems.

---

## BioBRIDGE Drug Embeddings

The embeddings used in this project were obtained from the public [BioBRIDGE repository](https://github.com/RyanWangZf/BioBridge).

BioBRIDGE is a biomedical representation learning framework that generates dense vector representations for biological entities by integrating knowledge graph structure and multimodal biological information.

In this work, BioBRIDGE drug embeddings are treated as pretrained representations and integrated into PrimeKG within Neo4j. 

---

## Technical Setup

- **Neo4j Kernel:** 2025.10.x (Enterprise)
- **Vector Index:** Native HNSW-based approximate nearest neighbor (ANN) index
- **Similarity function:** Cosine similarity
- **Embedding dimension:** 512

Embeddings are stored as node properties:

- `biobridge_emb` (LIST<FLOAT>, 512d)
- `biobridge_dim`
- `has_biobridge_emb`

Vector index creation:

```cypher
CREATE VECTOR INDEX drug_biobridge_emb_idx IF NOT EXISTS
FOR (d:drug) ON (d.biobridge_emb)
OPTIONS {
  indexConfig: {
    `vector.dimensions`: 512,
    `vector.similarity_function`: 'cosine'
  }
};

---

## System Architecture

The integration consists of two phases:

### Phase 1 – Embedding Alignment
- Load pretrained BioBRIDGE drug embeddings
- Align embeddings with PrimeKG using `node_index`
- Merge with drug metadata
- Produce `drug_emb_df.pkl`

### Phase 2 – Neo4j Vector Integration
- Pre-check mapping consistency between embeddings and Neo4j nodes
- Batch upload embeddings to Neo4j
- Attach embedding properties:
    - `biobridge_emb`
    - `biobridge_dim`
    - `has_biobridge_emb`
- Enable vector similarity search via native Neo4j HNSW index
