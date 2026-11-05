"""Llamadas a proveedores de IA sin dependencias adicionales."""
import json
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError, URLError

MODELS = {
    "OpenAI": "gpt-4.1-mini",
    "Gemini": "gemini-2.5-flash",
    "Claude": "claude-sonnet-4-5",
    "Grok": "grok-4",
}

def generate(provider, model, api_key, idea, tone, minutes):
    if not all([model.strip(), api_key.strip(), idea.strip()]):
        raise ValueError("Enter your API key, model, and idea.")
    system = (
        "You are a professional scriptwriter. Write ONLY the final script in natural, "
        "clear English, suitable for reading from a teleprompter. Do not add "
        "explanatory headings or Markdown. Tone: %s. Approximate duration: %s "
        "minutes (around %s words)." % (tone, minutes, minutes * 135)
    )
    headers = {"Content-Type": "application/json"}
    if provider == "Gemini":
        endpoint = "https://generativelanguage.googleapis.com/v1beta/models/" + quote(model, safe="") + ":generateContent"
        headers["x-goog-api-key"] = api_key
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": idea}]}]}
    elif provider == "Claude":
        endpoint = "https://api.anthropic.com/v1/messages"
        headers.update({"x-api-key": api_key, "anthropic-version": "2023-06-01"})
        body = {"model": model, "max_tokens": min(8192, max(1024, minutes * 250)),
                "system": system, "messages": [{"role": "user", "content": idea}]}
    else:
        endpoint = ("https://api.openai.com/v1/chat/completions" if provider == "OpenAI"
                    else "https://api.x.ai/v1/chat/completions")
        headers["Authorization"] = "Bearer " + api_key
        body = {"model": model, "messages": [{"role": "system", "content": system},
                                             {"role": "user", "content": idea}]}
    request = Request(endpoint, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=120) as response:
            data = json.load(response)
    except HTTPError as exc:
        try:
            error = json.loads(exc.read().decode("utf-8"))
            message = error.get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            message = ""
        raise RuntimeError(message or f"Provider HTTP error {exc.code}.") from exc
    except URLError as exc:
        raise RuntimeError(f"Connection error: {exc.reason}") from exc
    if provider == "Gemini":
        result = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    elif provider == "Claude":
        result = "".join(p.get("text", "") for p in data.get("content", []) if p.get("type") == "text")
    else:
        result = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not result.strip():
        raise RuntimeError("The provider returned no text. Check the model or content filters.")
    return result.strip()
