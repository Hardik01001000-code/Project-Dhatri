def process_prompt(text: str) -> str:
    """
    Core prompt processor for the brain microservice.
    Currently operating in echo mode: returns the input text as-is.

    Args:
        text (str): The prompt received from the user (typed or transcribed).

    Returns:
        str: The response from the brain microservice (same as input).
    """
    if not text or not text.strip():
        return ""
    
    return text.strip()
