import json
import threading
import time
from textwrap import shorten
import html

import markdown
from markdownify import markdownify as md
from openai import OpenAI
from ratelimit import limits, sleep_and_retry

from common.config import Config
from common.logger import get_logger
from core.entry_filter import filter_entry

config = Config()
llm_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)
file_lock = threading.Lock()
logger = get_logger(__name__)


def _preview(text: str, width: int = 120) -> str:
    cleaned = text.replace('\n', ' ').replace('\r', ' ').strip()
    return shorten(cleaned, width=width, placeholder='…')


@sleep_and_retry
@limits(calls=config.llm_RPM, period=60)
def process_entry(miniflux_client, entry):
    # Todo change to queue
    llm_result = ''
    entry_id = entry.get('id')
    feed = entry.get('feed', {})
    feed_title = feed.get('title')

    logger.info(
        'Processing entry | id=%s | feed="%s" | title="%s"',
        entry_id,
        feed_title,
        entry.get('title'),
    )

    for agent_name, agent_config in config.agents.items():
        agent_prompt = agent_config.get('prompt', '')
        if not filter_entry(config, (agent_name, agent_config), entry):
            logger.debug('Agent %s skipped by filters for entry %s', agent_name, entry_id)
            continue

        agent_start = time.time()
        if '${content}' in agent_prompt:
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": agent_prompt.replace('${content}', md(entry.get('content', '')))}
            ]
        else:
            messages = [
                {"role": "system", "content": agent_prompt},
                {"role": "user", "content": "\n---\n " + md(entry.get('content', ''))}
            ]

        try:
            completion = llm_client.chat.completions.create(
                model=config.llm_model,
                messages=messages,
                timeout=config.llm_timeout
            )
        except Exception as exc:
            logger.error('Agent %s failed to fetch LLM result for entry %s', agent_name, entry_id, exc_info=exc)
            raise

        response_content = completion.choices[0].message.content or ''
        duration = time.time() - agent_start
        logger.info(
            'Agent %s completed entry %s in %.2fs | preview="%s"',
            agent_name,
            entry_id,
            duration,
            _preview(response_content),
        )

        if agent_name == 'summary':
            entry_list = {
                'datetime': entry.get('created_at'),
                'category': feed.get('category', {}).get('title') if feed else None,
                'title': entry.get('title'),
                'content': response_content
            }
            with file_lock:
                try:
                    with open('entries.json', 'r') as file:
                        data = json.load(file)
                except (FileNotFoundError, json.JSONDecodeError):
                    data = []
                data.append(entry_list)
                with open('entries.json', 'w') as file:
                    json.dump(data, file, indent=4, ensure_ascii=False)
            logger.debug('Persisted summary snapshot for entry %s', entry_id)

        if agent_config.get('style_block'):
            formatted_block = (
                '<div style="border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px; '
                'margin: 16px 0; background-color: #f9fafb; box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);">'
                f'<div style="font-size: 1.05em; font-weight: 600; color: #374151; margin-bottom: 8px;">{agent_config.get("title", "")}</div>'
                '<pre style="white-space: pre-wrap; font-family: \"SFMono-Regular\", Menlo, Monaco, Consolas, \"Liberation Mono\", \"Courier New\", monospace; '
                'font-size: 0.96em; line-height: 1.6; color: #1f2937; margin: 0;">\n'
                f'{html.escape(response_content.strip())}\n'
                '</pre>'
                '</div><hr><br />'
            )
            llm_result = llm_result + formatted_block
        else:
            llm_result = llm_result + f"{agent_config.get('title', '')}{markdown.markdown(response_content)}<hr><br />"

    if llm_result:
        miniflux_client.update_entry(entry_id, content=llm_result + entry.get('content', ''))
        logger.info('Updated Miniflux entry %s with agent output', entry_id)
    else:
        logger.debug('No agent produced output for entry %s', entry_id)
