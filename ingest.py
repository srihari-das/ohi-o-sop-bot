import io

import chromadb
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from sentence_transformers import SentenceTransformer

from chunker import chunk_document
from config import get_config

DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
MODEL_CACHE_DIR = './model_cache'
CHROMA_DB_PATH = './chroma_db'
COLLECTION_NAME = 'sop_chunks'

# Module-level model cache so warm restarts skip re-loading
_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer('all-mpnet-base-v2', cache_folder=MODEL_CACHE_DIR)
    return _model


def _get_drive_service(service_account_path: str):
    creds = service_account.Credentials.from_service_account_file(
        service_account_path, scopes=DRIVE_SCOPES
    )
    return build('drive', 'v3', credentials=creds)


def _list_sop_docs(drive_service, folder_id: str) -> list[dict]:
    query = (
        f"'{folder_id}' in parents"
        " and mimeType='application/vnd.google-apps.document'"
        " and trashed=false"
    )
    results = drive_service.files().list(q=query, fields='files(id, name)').execute()
    return results.get('files', [])


def _export_doc_as_text(drive_service, file_id: str) -> str:
    request = drive_service.files().export_media(fileId=file_id, mimeType='text/plain')
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue().decode('utf-8')


def run_ingest():
    config = get_config()

    drive_service = _get_drive_service(config['GOOGLE_SERVICE_ACCOUNT_JSON'])
    model = get_embedding_model()

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    # Clear and rebuild collection on every run so it stays fresh
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION_NAME,
        metadata={'hnsw:space': 'cosine'},
    )

    docs = _list_sop_docs(drive_service, config['DRIVE_SOP_FOLDER_ID'])
    print(f'[ingest] Found {len(docs)} Google Docs in SOP folder')

    total_chunks = 0
    for doc in docs:
        doc_id = doc['id']
        doc_name = doc['name']

        text = _export_doc_as_text(drive_service, doc_id)
        chunks = chunk_document(text, doc_name)

        for c in chunks:
            print(f'  [chunk {c["chunk_index"]}] tier={c["chunking_tier"]}\n{c["text"]}\n{"-" * 60}')

        if not chunks:
            print(f'[ingest] "{doc_name}" produced no chunks — skipping')
            continue

        ids = [f'{doc_id}_{c["chunk_index"]}' for c in chunks]
        texts = [c['text'] for c in chunks]
        embeddings = model.encode(texts).tolist()
        metadatas = [
            {
                'source_doc_name': doc_name,
                'source_doc_id': doc_id,
                'chunk_index': c['chunk_index'],
                'chunking_tier': c['chunking_tier'],
            }
            for c in chunks
        ]

        collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        total_chunks += len(chunks)

    print(f'[ingest] Done — {len(docs)} docs, {total_chunks} total chunks stored in ChromaDB')
    return collection


if __name__ == '__main__':
    run_ingest()
