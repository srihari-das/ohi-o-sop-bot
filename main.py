import asyncio

import discord

from config import get_config
from groq_client import generate_answer
from ingest import run_ingest
from logger import log_query, verify_logging
from search import search


def _drive_folder_link(folder_id: str) -> str:
    return f'https://drive.google.com/drive/folders/{folder_id}'


async def handle_dm(message: discord.Message, config: dict) -> None:
    threshold = config['SIMILARITY_THRESHOLD']

    async with message.channel.typing():
        chunks = search(message.content)

        # --- No results at all ---
        if not chunks:
            await message.channel.send(
                "I couldn't find a confident match for that question.\n\n"
                f"You can browse the full SOP folder here: {_drive_folder_link(config['DRIVE_SOP_FOLDER_ID'])}\n\n"
                "*(This question has been logged — if it comes up a lot, it's worth adding to the SOPs.)*"
            )
            log_query(message.content, None, None, was_confident=False)
            return

        top = chunks[0]
        top_score = top['similarity_score']
        was_confident = top_score >= threshold

        if was_confident:
            # --- Try Groq ---
            try:
                answer = generate_answer(message.content, chunks)
                await message.channel.send(answer)
            except Exception as e:
                print(f'[main] Groq failed: {e} — falling back to raw chunk')
                doc_link = f'https://docs.google.com/document/d/{top["source_doc_id"]}'
                await message.channel.send(
                    f'Here\'s what I found in **{top["source_doc_name"]}**:\n\n'
                    f'{top["text"]}\n\n'
                    f'📄 Full doc: {doc_link}'
                )
        else:
            # --- Low confidence ---
            await message.channel.send(
                "I couldn't find a confident match for that question.\n\n"
                f"You can browse the full SOP folder here: {_drive_folder_link(config['DRIVE_SOP_FOLDER_ID'])}\n\n"
                "*(This question has been logged — if it comes up a lot, it's worth adding to the SOPs.)*"
            )

        log_query(message.content, top, top_score, was_confident)


def main() -> None:
    config = get_config(require_discord=True)

    print('[main] Verifying Google Sheets access...')
    verify_logging()

    print('[main] Running ingestion before connecting to Discord...')
    run_ingest()
    print('[main] Ingestion complete.\n')

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        print(f'[main] Logged in as {client.user} (id={client.user.id})')
        print('[main] Listening for DMs.')

    @client.event
    async def on_message(message: discord.Message) -> None:
        # Ignore the bot's own messages
        if message.author == client.user:
            return
        # Only respond to DMs
        if not isinstance(message.channel, discord.DMChannel):
            return

        print(f'[main] DM received from user id={message.author.id}')
        await handle_dm(message, config)

    client.run(config['DISCORD_BOT_TOKEN'])


if __name__ == '__main__':
    main()
