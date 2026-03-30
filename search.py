import chromadb

from ingest import CHROMA_DB_PATH, COLLECTION_NAME, get_embedding_model

TOP_K = 3


def search(query: str) -> list[dict] | None:
    """Find the top 3 most relevant SOP chunks for a query.

    Returns a list of dicts (sorted by descending similarity), each with keys:
        text, source_doc_name, source_doc_id, chunk_index, chunking_tier, similarity_score

    Returns None if the collection is empty.
    """
    model = get_embedding_model()
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_collection(COLLECTION_NAME)

    query_embedding = model.encode([query]).tolist()

    n = min(TOP_K, collection.count())
    if n == 0:
        return None

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=n,
        include=['documents', 'metadatas', 'distances'],
    )

    if not results['ids'][0]:
        return None

    chunks = []
    for text, metadata, distance in zip(
        results['documents'][0],
        results['metadatas'][0],
        results['distances'][0],
    ):
        similarity = 1 - distance
        chunks.append({
            'text': text,
            'source_doc_name': metadata['source_doc_name'],
            'source_doc_id': metadata['source_doc_id'],
            'chunk_index': metadata['chunk_index'],
            'chunking_tier': metadata['chunking_tier'],
            'similarity_score': similarity,
        })

    for i, c in enumerate(chunks):
        print(f'[search] result {i + 1}: score={c["similarity_score"]:.4f}  doc="{c["source_doc_name"]}"')

    return chunks
