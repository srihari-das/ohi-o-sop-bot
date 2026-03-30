"""CLI test harness for validating search quality without Discord.

Usage:
    python test.py                # re-ingests on startup
    python test.py --no-ingest    # reuses existing ChromaDB (faster iteration)
    python test.py --test-logging # verifies Sheets connection and writes a dummy row
"""
import argparse


def run_logging_test() -> None:
    from logger import log_query, verify_logging

    print('[test] Verifying Google Sheets connection...')
    try:
        verify_logging()
    except Exception as e:
        print(f'[test] FAILURE — could not connect to Google Sheets: {e}')
        return

    print('[test] Writing dummy test row...')
    try:
        dummy_result = {
            'text': 'This is a test chunk written by test.py --test-logging.',
            'source_doc_name': 'TEST DOCUMENT',
            'source_doc_id': 'test-id',
            'chunk_index': 0,
            'chunking_tier': 0,
        }
        log_query(
            question='[TEST] Logging verification query — safe to delete this row.',
            result=dummy_result,
            similarity_score=1.0,
            was_confident=True,
        )
        print('[test] SUCCESS — dummy row written to Google Sheets.')
    except Exception as e:
        print(f'[test] FAILURE — connection succeeded but could not write row: {e}')


def main() -> None:
    parser = argparse.ArgumentParser(description='CLI test harness for OHI/O SOP bot')
    parser.add_argument(
        '--no-ingest',
        action='store_true',
        help='Skip re-ingestion and reuse the existing ChromaDB',
    )
    parser.add_argument(
        '--test-logging',
        action='store_true',
        help='Verify Sheets connection and write a dummy log row, then exit',
    )
    args = parser.parse_args()

    if args.test_logging:
        run_logging_test()
        return

    if not args.no_ingest:
        print('[test] Running ingestion...\n')
        from ingest import run_ingest
        run_ingest()
        print()
    else:
        print('[test] Skipping ingestion — reusing existing ChromaDB\n')

    from config import get_config
    from groq_client import generate_answer
    from search import search

    config = get_config()
    threshold = config['SIMILARITY_THRESHOLD']

    print(f'[test] Similarity threshold: {threshold}')
    print('Type a question and press Enter. Type "quit" to exit.\n')

    while True:
        try:
            question = input('Ask a question (or "quit"): ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\n[test] Exiting.')
            break

        if question.lower() in ('quit', 'q', 'exit'):
            break
        if not question:
            continue

        chunks = search(question)

        if chunks is None:
            print('[test] No results found in ChromaDB.\n')
            continue

        print()
        for i, c in enumerate(chunks):
            print(f'--- Match {i + 1} ---')
            print(f'Source:        {c["source_doc_name"]} (chunk {c["chunk_index"]})')
            print(f'Similarity:    {c["similarity_score"]:.4f}')
            print(f'Chunking tier: {c["chunking_tier"]}')
            print(f'Chunk text:\n{c["text"]}')
            print()

        top_score = chunks[0]['similarity_score']
        if top_score >= threshold:
            print('[test] Above threshold — generating Groq answer...')
            try:
                answer = generate_answer(question, chunks)
                print(f'\nGroq answer:\n{answer}\n')
            except Exception as e:
                print(f'[test] Groq failed: {e}')
                print('[test] Fallback: raw top chunk shown above.\n')
        else:
            print(
                f'[test] Below threshold '
                f'({top_score:.4f} < {threshold}) — low confidence.\n'
            )


if __name__ == '__main__':
    main()
