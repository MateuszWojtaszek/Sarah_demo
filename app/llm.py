import os
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

NVIDIA_API_KEY_HIGH = os.environ["NVIDIA_API_KEY_HIGH"]
NVIDIA_API_KEY_FAST = os.environ["NVIDIA_API_KEY_FAST"]

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
# statystyki z przykładu nvidia, tak jak wiekszość kodu
MODELS = {
    "high": {
        "api_key": NVIDIA_API_KEY_HIGH,
        "model": "z-ai/glm-5.1",
        "temperature": 0.4,
        "top_p": 1,
        "max_tokens": 8192,  # Ustawienie bezpiecznego limitu API
        "extra_body": {
            "chat_template_kwargs": {
                "enable_thinking": True,
                "clear_thinking": False,
            }
        },
    },
    "fast": {
        "api_key": NVIDIA_API_KEY_FAST,
        "model": "qwen/qwen3-next-80b-a3b-thinking",
        "temperature": 0.6,
        "top_p": 0.7,
        "max_tokens": 8192,
        "extra_body": None,
    },
}


def generate_summary_stream(user_query, scraped_text, model_mode="high"):
    """
    Generator, który 'wypluwa' tokeny na żywo w miarę ich napływania z NVIDII.
    Zwraca krotkę: (typ_tekstu, fragment_tekstu)
    model_mode: "high" (GLM-5.1, głębokie rozumowanie) lub "fast" (Qwen3, szybszy)
    """
    cfg = MODELS.get(model_mode, MODELS["high"])
    client = OpenAI(base_url=NVIDIA_BASE_URL, api_key=cfg["api_key"])

    safe_text = scraped_text[:20000]

    system_prompt = """
    Jesteś analitycznym asystentem badawczym AI o imieniu Sarah.
    Twoim zadaniem jest napisanie ZWIĘZŁEGO, rzetelnego podsumowania (maksymalnie 6-7 akapitów) na podany temat,
    używając TYLKO dostarczonych poniżej fragmentów artykułów naukowych.

    ZASADY:
    1. Używaj TYLKO dostarczonych fragmentów. Nie dodawaj wiedzy zewnętrznej.
    2. Otrzymujesz od 1 do 3 ponumerowanych źródeł. NIE WYMYŚLAJ i nie wymieniaj źródeł (np. Source 4, Source 11), jeśli ich nie ma w tekście.
    3. Pisz w języku polskim, używając formatowania Markdown (nagłówki, listy).
    4. Bądź syntetyczna. Wyciągaj tylko esencję wiedzy badawczej. Masz krótki limit słów, więc zakończ podsumowanie naturalnie, zanim zostaniesz ucięta.
    """

    user_message = f"Temat do zbadania: {user_query}\n\nOto dostarczone teksty źródłowe:\n\n{safe_text}"

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        if cfg["extra_body"]:
            completion = client.chat.completions.create(
                model=cfg["model"],
                messages=messages,
                temperature=cfg["temperature"],
                top_p=cfg["top_p"],
                max_tokens=cfg["max_tokens"],
                extra_body=cfg["extra_body"],
                stream=True,
            )
        else:
            completion = client.chat.completions.create(
                model=cfg["model"],
                messages=messages,
                temperature=cfg["temperature"],
                top_p=cfg["top_p"],
                max_tokens=cfg["max_tokens"],
                stream=True,
            )

        in_think_tag = False

        for chunk in completion:
            if not getattr(chunk, "choices", None):
                continue
            if (
                len(chunk.choices) == 0
                or getattr(chunk.choices[0], "delta", None) is None
            ):
                continue

            delta = chunk.choices[0].delta

            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield ("reasoning", reasoning)

            content = getattr(delta, "content", None)
            if content is not None:
                # Logika odcinania <think> dla modeli bez natywnego wsparcia (jak Qwen)
                if "<think>" in content:
                    in_think_tag = True
                    content = content.replace("<think>", "")

                if "</think>" in content:
                    in_think_tag = False
                    parts = content.split("</think>")
                    if parts[0]:
                        yield ("reasoning", parts[0])
                    if len(parts) > 1 and parts[1]:
                        yield ("content", parts[1])
                    continue

                if in_think_tag:
                    yield ("reasoning", content)
                else:
                    yield ("content", content)

    except Exception as e:
        yield ("error", f" Wystąpił błąd LLM: {str(e)}")
