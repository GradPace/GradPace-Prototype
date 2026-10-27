"""Client for the self-hosted LLM - llama.cpp's llama-server running gemma-4
E2B on CPU (k8s/llama-deployment.yaml), through its OpenAI-compatible
/v1/chat/completions endpoint.

The server has a single inference slot, so callers should keep prompts and
max_tokens small, and treat LLMUnavailable as an expected outcome (the pod
restarting, a slow answer timing out, or another request holding the slot)
rather than a bug."""

import json
import urllib.error
import urllib.request

from django.conf import settings


class LLMUnavailable(Exception):
    """The model couldn't produce a usable answer - unreachable, timed out,
    returned an error, or replied with something that isn't the JSON asked
    for."""


def chat_json(messages, *, schema=None, max_tokens=512):
    """Sends `messages` (OpenAI chat format) and returns the model's reply
    parsed as JSON. With `schema` (a JSON Schema dict), llama-server
    constrains generation to it, so the reply matches its shape; without one,
    the reply is only guaranteed to be some JSON object.

    Raises LLMUnavailable on any failure."""
    if schema is None:
        response_format = {'type': 'json_object'}
    else:
        response_format = {'type': 'json_schema', 'json_schema': {'schema': schema}}

    body = {
        'messages': messages,
        'max_tokens': max_tokens,
        'response_format': response_format,
        # Thinking on makes E2B ~25x slower and puts its reasoning ahead of
        # the JSON - off for anything a user is waiting on.
        'chat_template_kwargs': {'enable_thinking': False},
    }

    try:
        chat_request = urllib.request.Request(
            f'{settings.LLAMA_CPP_BASE_URL}/v1/chat/completions',
            data=json.dumps(body).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': 'gradpace-backend'},
        )
        with urllib.request.urlopen(chat_request, timeout=settings.LLAMA_CPP_TIMEOUT) as response:
            result = json.load(response)
        return json.loads(result['choices'][0]['message']['content'])
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        # Not JSON (ValueError), or JSON without the completion's shape.
        ValueError,
        KeyError,
        IndexError,
        TypeError,
    ):
        raise LLMUnavailable from None
