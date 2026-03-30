# OHI/O SOP Bot

A Discord bot for OHI/O that lets members privately ask questions about the org and get answers sourced from SOP documents stored in Google Drive. The bot responds via DM only, so questions and answers stay private. All queries are logged anonymously to a Google Sheet so future leads can identify gaps in the SOPs.

---

## How it works

1. On startup, the bot pulls all Google Docs from a designated Drive folder, chunks them using a hybrid strategy, and embeds each chunk into a local ChromaDB vector store.
2. When a member DMs the bot a question, it finds the most semantically relevant chunk using cosine similarity search.
3. If the match is confident, it passes the chunk and question to Groq's LLM to generate a conversational answer with a source citation.
4. If no confident match is found, it returns a fallback message with a link to the SOP folder.
5. Every query is logged to a Google Sheet regardless of confidence, so low-confidence queries surface SOP gaps over time.

---

## Stack

| Component | Choice |
|---|---|
| Discord interface | `discord.py` |
| Embedding model | `sentence-transformers` (`all-mpnet-base-v2`) |
| Vector database | ChromaDB (persisted locally) |
| LLM | Groq API (`llama-3.3-70b-versatile`) |
| SOP source | Google Drive API |
| Logging | `gspread` to Google Sheets |
| Hosting | Railway |

---

## Hybrid chunking

SOP authors are not required to use specific formatting. The chunker uses a three-tier fallback:

- **Tier 1 (header-based):** If the doc has 3+ detectable headers, splits on those. Each chunk includes its header as the first line for embedding context.
- **Tier 2 (paragraph-based):** If fewer than 3 headers are detected, splits on blank lines and merges short consecutive paragraphs.
- **Tier 3 (fixed-size fallback):** For unstructured walls of text, splits into 400-token chunks with 50-token overlap.

Which tier was used is logged during ingestion and stored per chunk in ChromaDB, giving maintainers visibility into which SOPs need formatting improvements.

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/ohio-sop-bot.git
cd ohio-sop-bot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up Google Cloud

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project
2. Enable the **Google Drive API** and **Google Sheets API**
3. Go to **IAM & Admin → Service Accounts → Create Service Account**
4. Under the **Keys** tab, click **Add Key → Create new key → JSON** and download the file
5. Place the JSON file in the project root (it is gitignored)
6. Copy the service account email from the JSON (`client_email` field)
7. Share your **SOP folder** in Drive with that email (Viewer access)
8. Share your **Query Log Google Sheet** with that email (Editor access)

### 4. Create a Discord bot

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications) and create a new application
2. Under the **Bot** tab, click **Add Bot** and copy the token
3. Enable **Message Content Intent** under Privileged Gateway Intents
4. Use the OAuth2 URL Generator to invite the bot to a server (scopes: `bot`, permissions: `Send Messages`, `Read Message History`)

### 5. Configure environment variables

Copy `.env.example` to `.env` and fill in all values:

```
DISCORD_BOT_TOKEN=
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
DRIVE_SOP_FOLDER_ID=
DRIVE_LOG_SHEET_ID=
GROQ_API_KEY=
SIMILARITY_THRESHOLD=0.3
```

Get `DRIVE_SOP_FOLDER_ID` from the URL of your SOP folder in Drive (`/folders/YOUR_ID_HERE`).
Get `DRIVE_LOG_SHEET_ID` from the URL of your Query Log sheet (`/d/YOUR_ID_HERE/edit`).
Get your Groq API key at [console.groq.com](https://console.groq.com).

---

## Testing without Discord

Use the CLI test harness to validate search quality before wiring up the bot:

```bash
python test.py
```

This ingests your SOPs, drops into an interactive prompt, and prints similarity scores and Groq answers for each query. Use it to calibrate `SIMILARITY_THRESHOLD` against real questions before going live.

```bash
python test.py --no-ingest   # skip re-ingestion, reuse existing ChromaDB
python test.py --test-logging  # verify Google Sheets connection and write a test row
```

---

## Running the bot

```bash
python main.py
```

The bot ingests all SOPs on startup before connecting to Discord, so it is never live with a stale index. DM it any question and it will respond privately.

---

## Deployment (Railway)

1. Push the repo to GitHub (`.env` and `service_account.json` are gitignored)
2. Create a new Railway project and connect the GitHub repo
3. Add all environment variables from `.env` in the Railway dashboard
4. Upload `service_account.json` as a file in Railway and set `GOOGLE_SERVICE_ACCOUNT_JSON` to its path
5. Railway auto-deploys on every push to main

The embedding model (~420MB) is cached after first boot so warm restarts are fast. Groq handles all LLM inference remotely on the free tier.

---

## Google Sheet schema

| timestamp | question | matched_chunk | source_doc | similarity_score | was_confident | chunking_tier |
|---|---|---|---|---|---|---|

Headers are written automatically on first connection if the sheet is empty.

---

## Future improvements

- Support PDF SOPs via `pdfplumber` (currently Google Docs only)
- Return top 2-3 chunks for complex multi-part questions
- Weekly digest of the most common low-confidence queries emailed to current leads
- Slash command `/sop refresh` to manually trigger re-ingestion without a full restart
- SOP health report based on chunking tier logs showing which docs need formatting improvements
