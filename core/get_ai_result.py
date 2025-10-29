from textwrap import shorten

from openai import OpenAI

from common.config import Config
from common.logger import get_logger

config = Config()
llm_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)
logger = get_logger(__name__)


def _preview(text: str) -> str:
    return shorten(text.replace('\n', ' ').strip(), width=120, placeholder='…')


def get_ai_result(prompt, request):
    logger.debug('Executing AI helper prompt | preview="%s"', _preview(prompt))
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": request + "\n---\n" + prompt
        }
    ]

    try:
        completion = llm_client.chat.completions.create(
            model=config.llm_model,
            messages=messages,
            timeout=config.llm_timeout
        )
    except Exception as exc:
        logger.error('AI helper prompt failed to execute', exc_info=exc)
        raise

    response_content = completion.choices[0].message.content
    logger.debug('AI helper prompt completed | preview="%s"', _preview(response_content))
    return response_content
