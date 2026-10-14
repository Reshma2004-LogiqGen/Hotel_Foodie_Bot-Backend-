"""
Food Friend Backend - OpenAI service
All AI calls (chat personas and nutrition) go through here.
"""

import json
import logging
import os

import openai
from openai import OpenAI

log = logging.getLogger(__name__)

DEFAULT_MODEL = 'gpt-5.4-mini'
REQUEST_TIMEOUT_SECONDS = 30


class AIUnavailableError(Exception):
    """The AI could not answer. The message is safe to show to customers."""

    def __init__(self, message, status=503):
        super().__init__(message)
        self.status = status


def _not_configured():
    return AIUnavailableError("The AI assistant isn't set up yet. Please ask the staff.")


def _not_reachable():
    return AIUnavailableError("The AI assistant can't be reached right now. Please try again.", 502)


def _busy():
    return AIUnavailableError('The AI assistant is busy right now. Please try again in a moment.', 429)


_client = None


def model_name():
    return os.getenv('OPENAI_MODEL') or DEFAULT_MODEL


def is_configured():
    return bool(os.getenv('OPENAI_API_KEY'))


def _get_client():
    global _client
    if not is_configured():
        raise _not_configured()
    if _client is None:
        _client = OpenAI(timeout=REQUEST_TIMEOUT_SECONDS, max_retries=2)
    return _client


def _respond(**kwargs):
    try:
        response = _get_client().responses.create(model=model_name(), store=False, **kwargs)
    except openai.RateLimitError as error:
        log.error('OpenAI rate limit or quota: %s', error)
        raise _busy() from error
    except (openai.AuthenticationError, openai.PermissionDeniedError, openai.NotFoundError) as error:
        log.error('OpenAI key or model problem (check OPENAI_API_KEY / OPENAI_MODEL): %s', error)
        raise _not_configured() from error
    except openai.OpenAIError as error:
        log.error('OpenAI request failed: %s', error)
        raise _not_reachable() from error

    text = (response.output_text or '').strip()
    if response.status == 'incomplete' or not text:
        log.error('OpenAI returned no usable text (status=%s, details=%s)', response.status, response.incomplete_details)
        raise _not_reachable()
    return text


def chat_reply(instructions, messages, user_id):
    """One persona reply. `messages` is a list of {'role': 'user'|'assistant', 'content': str}."""
    return _respond(
        instructions=instructions,
        input=messages,
        reasoning={'effort': 'none'},
        max_output_tokens=200,
        safety_identifier=user_id,
    )


def structured(instructions, prompt, schema_name, schema, user_id):
    """A JSON answer that always matches `schema`."""
    text = _respond(
        instructions=instructions,
        input=prompt,
        reasoning={'effort': 'low'},
        max_output_tokens=4000,
        text={'format': {'type': 'json_schema', 'name': schema_name, 'schema': schema, 'strict': True}},
        safety_identifier=user_id,
    )
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        log.error('OpenAI returned invalid JSON for %s: %s', schema_name, text[:200])
        raise _not_reachable() from error
