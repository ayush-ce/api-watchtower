from datetime import datetime, timedelta

import tiktoken

MAX_TOKENS = 7000
CHUNK_SIZE = 3000

encoding = tiktoken.encoding_for_model("gpt-4")


def num_tokens_from_string(string: str) -> int:
    return len(encoding.encode(string))


def chunk_text(text: str, chunk_size: int):
    tokens = encoding.encode(text)
    chunks = [tokens[i : i + chunk_size] for i in range(0, len(tokens), chunk_size)]
    print(
        f"📦 Splitting text into {len(chunks)} chunks of up to {chunk_size} tokens each."
    )
    return [encoding.decode(chunk) for chunk in chunks]


def get_serp_date_range(days_ago):
    today = datetime.today()
    past_date = today - timedelta(days=days_ago)
    return (
        past_date.strftime("%m/%d/%Y"),
        today.strftime("%m/%d/%Y"),
    )


def get_tavily_date_range(days_ago):
    today = datetime.today()
    past_date = today - timedelta(days=days_ago)
    return (
        past_date.strftime("%Y-%m-%d"),
        today.strftime("%Y-%m-%d"),
    )
