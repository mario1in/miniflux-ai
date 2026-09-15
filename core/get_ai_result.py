import re
from textwrap import shorten

from markdownify import markdownify as md
from openai import OpenAI
from google import genai
from google.genai import types

from common.config import Config
from common.logger import get_logger

config = Config()
logger = get_logger(__name__)

if not config.llm_provider or config.llm_provider == "openai":
    llm_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)
elif config.llm_provider == "gemini":
    llm_client = genai.Client(
        http_options=types.HttpOptions(base_url=config.llm_base_url),
        api_key=config.llm_api_key,
    )
else:
    raise ValueError(f'Unsupported llm.provider: {config.llm_provider}')


def _preview(text, width: int = 120) -> str:
    return shorten((text or '').replace('\n', ' ').strip(), width=width, placeholder='…')


_MD_IMAGE_RE = re.compile(r'!\[[^\]]*\]\([^)]*\)')


def to_markdown(request: str) -> str:
    """HTML → markdown for the model. Images carry nothing a summary or a translation can use, and a model
    asked to keep the formatting would echo them back as ![](…) lines."""
    text = _MD_IMAGE_RE.sub('', md(request or ''))
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def get_ai_result(prompt: str, request: str):
    if config.llm_max_length and len(request) > config.llm_max_length:
        request = request[: config.llm_max_length]
    logger.debug('Executing AI prompt | preview="%s"', _preview(prompt))

    if config.llm_provider == "gemini":
        try:
            if "${content}" in prompt:
                instruction = ["You are a helpful assistant."]
                contents = prompt.replace("${content}", to_markdown(request))
            else:
                instruction = [prompt]
                contents = "The following is the input content:\n---\n " + to_markdown(request)

            response = llm_client.models.generate_content(
                model=config.llm_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=instruction,
                    **config.llm_extra_params,
                ),
            )
            logger.debug('AI prompt completed (Gemini) | preview="%s"', _preview(response.text))
            return response.text
        except Exception as exc:
            logger.error('Error in get_ai_result (Gemini): %s', exc)
            logger.debug('Gemini traceback', exc_info=exc)
            raise
    else:
        if "${content}" in prompt:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt.replace("${content}", to_markdown(request))},
            ]
        else:
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": "The following is the input content:\n---\n " + to_markdown(request)},
            ]

        try:
            completion = llm_client.chat.completions.create(
                model=config.llm_model,
                messages=messages,
                timeout=config.llm_timeout,
                **config.llm_extra_params,
            )
            response_content = completion.choices[0].message.content
            logger.debug('AI prompt completed (OpenAI) | preview="%s"', _preview(response_content))
            return response_content
        except Exception as exc:
            logger.error('Error in get_ai_result (OpenAI): %s', exc)
            logger.debug('OpenAI traceback', exc_info=exc)
            raise
