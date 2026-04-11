"""
LLM provider abstraction using LangChain.
Switch providers by setting LLM_PROVIDER env var:

  openai    → gpt-4o-mini (default)
  anthropic → claude-3-5-haiku-20241022
  groq      → llama-3.3-70b-versatile
  ollama    → llama3.2 (self-hosted)
"""
import os
import logging
from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)

PROVIDER = os.getenv("LLM_PROVIDER", "openai")
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")


def get_llm(temperature: float = 0.2, streaming: bool = False) -> BaseChatModel:
    """Return a LangChain chat model for the configured provider."""

    if PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=MODEL,
            temperature=temperature,
            streaming=streaming,
            api_key=os.environ["OPENAI_API_KEY"],
        )

    elif PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=MODEL,
            temperature=temperature,
            streaming=streaming,
            api_key=os.environ["ANTHROPIC_API_KEY"],
        )

    elif PROVIDER == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=MODEL,
            temperature=temperature,
            streaming=streaming,
            api_key=os.environ["GROQ_API_KEY"],
        )

    elif PROVIDER == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=MODEL,
            temperature=temperature,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {PROVIDER!r}. Choose: openai, anthropic, groq, ollama")
