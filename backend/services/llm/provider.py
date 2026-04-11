"""
LLM provider abstraction using LangChain.
Switch providers by setting LLM_PROVIDER env var:

  openai    → gpt-4o-mini (default)
  google    → gemini-2.0-flash
  anthropic → claude-3-5-haiku-20241022
  groq      → llama-3.3-70b-versatile
  openrouter→ any model via openrouter.ai (OpenAI-compatible)
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

    elif PROVIDER == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=MODEL or "gemini-2.0-flash",
            temperature=temperature,
            google_api_key=os.environ["GOOGLE_API_KEY"],
            # Gemini streaming works differently — LangChain handles it transparently
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

    elif PROVIDER == "openrouter":
        # OpenRouter exposes an OpenAI-compatible API — supports Qwen, Kimi, Mistral, etc.
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=MODEL,
            temperature=temperature,
            streaming=streaming,
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": os.getenv("APP_URL", "https://recalls-chatbot.up.railway.app"),
                "X-Title": "CPSC Recalls Chatbot",
            },
        )

    elif PROVIDER == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=MODEL,
            temperature=temperature,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: {PROVIDER!r}. "
            "Choose: openai, google, anthropic, groq, openrouter, ollama"
        )
