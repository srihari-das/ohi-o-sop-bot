import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED_VARS = [
    'GOOGLE_SERVICE_ACCOUNT_JSON',
    'DRIVE_SOP_FOLDER_ID',
    'DRIVE_LOG_SHEET_ID',
    'GROQ_API_KEY',
]

# Only required when running the Discord bot (main.py)
DISCORD_REQUIRED_VARS = [
    'DISCORD_BOT_TOKEN',
]

_config = None


def get_config(require_discord: bool = False) -> dict:
    global _config
    if _config is not None:
        return _config

    check = REQUIRED_VARS + (DISCORD_REQUIRED_VARS if require_discord else [])
    missing = [v for v in check if not os.getenv(v)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Check your .env file."
        )

    _config = {
        'DISCORD_BOT_TOKEN': os.getenv('DISCORD_BOT_TOKEN'),  # None if not set
        'GOOGLE_SERVICE_ACCOUNT_JSON': os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'),
        'DRIVE_SOP_FOLDER_ID': os.getenv('DRIVE_SOP_FOLDER_ID'),
        'DRIVE_LOG_SHEET_ID': os.getenv('DRIVE_LOG_SHEET_ID'),
        'GROQ_API_KEY': os.getenv('GROQ_API_KEY'),
        'SIMILARITY_THRESHOLD': float(os.getenv('SIMILARITY_THRESHOLD', '0.4')),
    }

    return _config
