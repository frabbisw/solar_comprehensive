"""
shared/llm_client.py

Single LLM gateway. Configure the model version in .env:
    OPENAI_MODEL=gpt-3.5-turbo

All agents call chat() without worrying about model version strings.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_gpt_client   = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_MODEL_VERSION = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")


def chat(
    system: str,
    user: str,
    model: str = "gpt",
    temperature: float = 1.0,
    max_tokens: int = 1024,
) -> str:
    if model == "gpt":
        return _call_gpt(system, user, temperature, max_tokens)
    elif model in ("llama", "bison", "claude"):
        raise NotImplementedError(f"Model '{model}' is not active. Add credentials and uncomment in llm_client.py")
    else:
        raise ValueError(f"Unknown model '{model}'. Choose from: gpt, llama, bison, claude.")


def _call_gpt(system: str, user: str, temperature: float, max_tokens: int) -> str:
    response = _gpt_client.chat.completions.create(
        model=_MODEL_VERSION,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return (response.choices[0].message.content or "").strip()
