import tiktoken


def get_tokenizer(model: str):
    try:
        tokenizer = tiktoken.encoding_for_model(model).encode
    except KeyError:
        tokenizer = tiktoken.get_encoding("cl100k_base").encode
    return tokenizer

def count_tokens(text: str, model: str) -> int:
    tokenizer = get_tokenizer(model)

    if tokenizer:
        return len(tokenizer(text))
    
    return estimate_token(text)

def estimate_token(text: str) -> int:
    # Rough estimate: 1 token ~ 4 characters in English text
    return max(1, len(text) // 4)