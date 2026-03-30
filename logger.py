from datetime import datetime, timezone

import gspread

from config import get_config

_sheet_cache = None


def _get_sheet():
    global _sheet_cache
    if _sheet_cache is not None:
        return _sheet_cache
    config = get_config()
    gc = gspread.service_account(filename=config['GOOGLE_SERVICE_ACCOUNT_JSON'])
    _sheet_cache = gc.open_by_key(config['DRIVE_LOG_SHEET_ID']).sheet1
    return _sheet_cache


_HEADERS = [
    'timestamp', 'question', 'matched_chunk', 'source_doc',
    'similarity_score', 'was_confident', 'chunking_tier',
]


def verify_logging() -> None:
    """Call at startup to confirm Sheets access works. Raises on failure."""
    sheet = _get_sheet()
    if not sheet.row_values(1):
        sheet.append_row(_HEADERS)
        print('[logger] Google Sheets connection verified — header row written.')
    else:
        print('[logger] Google Sheets connection verified.')


def log_query(
    question: str,
    result: dict | None,
    similarity_score: float | None,
    was_confident: bool,
) -> None:
    """Append one row to the Query Log sheet.

    Logs ALL queries including low-confidence ones — these are the most
    valuable signal for SOP gaps. Never logs the Discord user's identity.
    """
    try:
        sheet = _get_sheet()
        timestamp = datetime.now(timezone.utc).isoformat()

        if result:
            matched_chunk = result['text'][:300]
            source_doc = result['source_doc_name']
            chunking_tier = result['chunking_tier']
        else:
            matched_chunk = ''
            source_doc = ''
            chunking_tier = ''

        row = [
            timestamp,
            question,
            matched_chunk,
            source_doc,
            round(similarity_score, 4) if similarity_score is not None else '',
            was_confident,
            chunking_tier,
        ]

        sheet.append_row(row)
    except Exception as e:
        print(f'[logger] Warning: failed to log query — {e}')
