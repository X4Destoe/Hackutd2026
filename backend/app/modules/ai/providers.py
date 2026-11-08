"""Optional SDK adapters. Importing this module does not load any SDK."""
import json
from typing import Protocol

DEFAULT_MODELS = {'anthropic': 'claude-sonnet-5-5', 'openai': 'gpt-4.1-mini', 'gemini': 'gemini-2.5-flash'}


class Provider(Protocol):
    def json(self, system: str, user: str, schema: dict, timeout: float) -> dict: ...
    def text(self, system: str, user: str, max_chars: int, timeout: float) -> str: ...


class SDKProvider:
    def __init__(self, name: str, model: str, key: str):
        self.name, self.model, self.key = name, model, key

    def text(self, system, user, max_chars, timeout):
        if self.name == 'anthropic':
            import anthropic
            with anthropic.Anthropic(api_key=self.key, timeout=timeout, max_retries=0) as client:
                response = client.messages.create(model=self.model, max_tokens=1600, system=system, messages=[{'role': 'user', 'content': user}])
                return ''.join(block.text for block in response.content if block.type == 'text')
        if self.name == 'openai':
            import openai
            with openai.OpenAI(api_key=self.key, timeout=timeout, max_retries=0) as client:
                response = client.chat.completions.create(model=self.model, max_tokens=1600, messages=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}])
                return response.choices[0].message.content or ''
        from google import genai
        from google.genai import types
        with genai.Client(api_key=self.key, http_options=types.HttpOptions(timeout=int(timeout * 1000), retry_options=types.HttpRetryOptions(attempts=1))) as client:
            response = client.models.generate_content(model=self.model, contents=user, config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=1600))
            return response.text or ''

    def json(self, system, user, schema, timeout):
        raw = self.text(system + '\nReturn only a JSON object matching this schema: ' + json.dumps(schema), user, 2000, timeout)
        return json.loads(raw)
