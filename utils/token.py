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


def truncate_text(
    text: str,
    model: str,
    max_tokens: int,
    suffix: str = "\n... [truncated]",
    preserver_lines: bool = True,
) -> str:
    current_tokens = count_tokens(text=text, model=model)
    if current_tokens <= max_tokens:
        return text

    suffix_tokens = count_tokens(suffix, model)
    target_tokens = max_tokens - suffix_tokens

    if target_tokens <= 0:
        return suffix.strip()

    if preserver_lines:
        return _truncate_by_lines(text, target_tokens, model, suffix)
    else:
        return _truncate_by_chars(text, target_tokens, suffix, model)


def _truncate_by_lines(
    text: str, 
    target_tokens: int, 
    model: str, 
    suffix: str
) -> str:
    lines = text.split("\n")
    result_lines: list[str] = []
    current_tokens = 0

    for line in lines:
        line_tokens = count_tokens(text=line + "\n", model=model)
        if current_tokens + line_tokens > target_tokens:
            break

        result_lines.append(line)
        current_tokens += line_tokens

    if not result_lines:
        return _truncate_by_chars(
            text=text, 
            target_tokens=target_tokens,
            model=model,
            suffix=suffix
        )

    return "\n".join(result_lines) + suffix


def _truncate_by_chars(
    text: str,
    target_tokens: int,
    model: str,
    suffix: str
)-> str:
    low, high = 0, len(text)
    
    while low < high:
        mid = (low + high + 1) // 2
        if count_tokens(text[:mid], model) <= target_tokens:
            low = mid
        else:
            high = mid - 1

    return text[:low] + suffix
