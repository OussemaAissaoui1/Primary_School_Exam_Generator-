"""Shared LLM helper — instantiates ChatGroq with automatic retry on rate-limit."""

import os
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

# Use llama-3.3-70b-versatile for best quality and to avoid rate limiting
_DEFAULT_MODEL = "llama-3.3-70b-versatile"
_MAX_RETRIES = 3
_RETRY_BASE_WAIT = 20  # seconds


def get_llm(temperature: float = 0.3, max_tokens: int = 4096,
            model: str = _DEFAULT_MODEL) -> ChatGroq:
    """Return a ChatGroq instance."""
    return ChatGroq(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def invoke_with_retry(chain, inputs: dict, max_retries: int = _MAX_RETRIES):
    """Invoke a LangChain chain with automatic back-off on 429 rate-limit."""
    for attempt in range(1, max_retries + 1):
        try:
            return chain.invoke(inputs)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate_limit" in err_str.lower():
                wait = _RETRY_BASE_WAIT * attempt
                print(f"[LLM] Rate-limit hit (attempt {attempt}/{max_retries}), "
                      f"waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    # Final attempt — let it raise naturally
    return chain.invoke(inputs)
