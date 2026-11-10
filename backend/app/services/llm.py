
from openai import OpenAI

from app.config import settings


def get_llm_client():
    provider = settings.llm_provider.lower()

    if provider == "groq":
        api_key = settings.groq_api_key
        base_url = "https://api.groq.com/openai/v1"

    elif provider == "openrouter":
        api_key = settings.openrouter_api_key
        base_url = "https://openrouter.ai/api/v1"

    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

    if not api_key:
        raise ValueError(f"API key is missing for {provider}")

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=60.0,
    )


class LLMResponse:
    def __init__(self, content: str):
        self.content = content


class LLMService:
    """Provides a simple invoke interface for research agents."""

    def __init__(self):
        self.client = get_llm_client()

    def invoke(
        self,
        prompt: str,
        max_tokens: int = 1500,
        temperature: float = 0,
        response_format: dict | None = None,
    ):
        request = {
            "model": settings.llm_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a careful research assistant. "
                        "Follow the user's instructions and never invent facts."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if response_format:
            request["response_format"] = response_format

        response = self.client.chat.completions.create(**request)

        content = response.choices[0].message.content

        if not content:
            raise ValueError("The LLM returned an empty response.")

        return LLMResponse(content)


def get_llm():
    """Return the LLM service used by research agents."""
    return LLMService()


def generate_answer(question: str, context: str) -> str:
    client = get_llm_client()

    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {
                "role": "system",
                "content": """
You are ResearchMind AI, a document-grounded research assistant.

Answer the user's question using the provided context.

Rules:
1. Prioritize information from the provided context.
2. Do not invent facts or references.
3. If the context does not contain enough information,
   clearly say so.
4. Cite supporting sources using their labels,
   for example [Source 1, Page 2].
5. Distinguish facts from reasonable interpretations.
6. Give a clear and organized answer.
""",
            },
            {
                "role": "user",
                "content": f"""
CONTEXT:
{context}

QUESTION:
{question}

Answer using the context and include source citations.
""",
            },
        ],
        temperature=0.2,
        max_tokens=1500,
    )

    answer = response.choices[0].message.content

    if not answer:
        raise ValueError("The LLM returned an empty response.")

    return answer
