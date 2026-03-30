from groq import Groq

from config import get_config

_SYSTEM_PROMPT = (
    "You are a helpful assistant for a student organization called OHI/O. "
    "You will be given several excerpts from SOP documents, each labeled with its source. "
    "Answer the user's question using only the excerpts that are directly relevant to it. "
    "If an excerpt is not directly related to the question, ignore it entirely — do not pad "
    "the answer with tangential information. "
    "Include all specific details from relevant excerpts: names, locations, tools, steps, "
    "contacts, or procedures that directly answer the question. "
    "Aim for 2-3 sentences for simple questions, and one focused paragraph for complex ones. "
    "Write in a conversational tone, as if explaining to a new org member. "
    "At the end of your answer, cite only the source document(s) you actually drew from, "
    "using the format: 'Source: <doc name> — <link>'. "
    "The link for each document is provided in the excerpts header. "
    "If the answer is not contained in any of the excerpts, say exactly: "
    "'I don't know based on the available SOPs.' "
    "Do not make up information or draw on outside knowledge."
)


def generate_answer(question: str, chunks: list[dict]) -> str:
    """Call the Groq API and return an answer synthesized from multiple chunks.

    Args:
        question: The user's question.
        chunks: List of result dicts from search.py, each with 'text' and 'source_doc_name'.

    Raises an exception on API failure so the caller can fall back gracefully.
    """
    config = get_config()
    client = Groq(api_key=config['GROQ_API_KEY'])

    excerpts = '\n\n'.join(
        f'[Excerpt {i + 1} — {c["source_doc_name"]} — '
        f'https://docs.google.com/document/d/{c["source_doc_id"]}]\n{c["text"]}'
        for i, c in enumerate(chunks)
    )

    user_message = f'Excerpts:\n{excerpts}\n\nQuestion: {question}'

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {'role': 'system', 'content': _SYSTEM_PROMPT},
            {'role': 'user', 'content': user_message},
        ],
        temperature=0.3,
        max_tokens=512,
    )

    return response.choices[0].message.content.strip()
