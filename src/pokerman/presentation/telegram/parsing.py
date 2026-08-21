def parse_positive_amount(text: str) -> int | None:
    try:
        amount = int(text.strip())
    except ValueError:
        return None
    return amount if amount > 0 else None
