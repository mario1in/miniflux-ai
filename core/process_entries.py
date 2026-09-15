import html
import json
import threading
import time
from textwrap import shorten

import markdown
from ratelimit import limits, sleep_and_retry

from common.config import Config
from common.logger import get_logger
from core.entry_filter import filter_entry
from core.get_ai_result import get_ai_result

config = Config()
file_lock = threading.Lock()
logger = get_logger(__name__)


def _preview(text: str, width: int = 120) -> str:
    cleaned = (text or '').replace('\n', ' ').replace('\r', ' ').strip()
    return shorten(cleaned, width=width, placeholder='…')


@sleep_and_retry
@limits(calls=config.llm_RPM, period=60)
def process_entry(miniflux_client, entry):
    # Todo change to queue
    llm_result = ''
    entry_id = entry.get('id')
    feed = entry.get('feed') or {}
    feed_title = feed.get('title')

    logger.debug('Processing entry | id=%s | feed="%s" | title="%s"', entry_id, feed_title, entry.get('title'))

    for agent_name, agent_config in config.agents.items():
        if not filter_entry(config, (agent_name, agent_config), entry):
            logger.debug('Agent %s skipped by filters for entry %s', agent_name, entry_id)
            continue

        agent_start = time.time()
        try:
            response_content = get_ai_result(agent_config.get('prompt', ''), entry.get('content', ''))
        except Exception as exc:
            logger.error('Agent %s failed for entry %s: %s', agent_name, entry_id, exc)
            logger.debug('Agent traceback', exc_info=exc)
            continue

        response_content = (response_content or '').strip()
        if not response_content:
            logger.warning('Agent %s returned empty output for entry %s', agent_name, entry_id)
            continue

        logger.info(
            'Agent %s completed entry %s in %.2fs | feed="%s" | preview="%s"',
            agent_name,
            entry_id,
            time.time() - agent_start,
            feed_title,
            _preview(response_content),
        )

        # save for ai_summary
        if agent_name == 'summary':
            entry_list = {
                'datetime': entry.get('created_at'),
                'category': (feed.get('category') or {}).get('title'),
                'title': entry.get('title'),
                'content': response_content,
                'url': entry.get('url'),
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
            # Keep the LLM's line breaks; the leading <blockquote> is also the "already processed" marker used by entry_filter
            body = html.escape(response_content).replace('\n', '<br>')
            llm_result = (llm_result + '<blockquote>\n  <p><strong>'
                          + agent_config.get('title', '') + '</strong> '
                          + body
                          + '\n</p>\n</blockquote><br/>')
        else:
            llm_result = llm_result + f"{agent_config.get('title', '')}{markdown.markdown(response_content)}<hr><br />"

    if llm_result:
        miniflux_client.update_entry(entry_id, content=llm_result + entry.get('content', ''))
        logger.info('Updated Miniflux entry %s with agent output', entry_id)
    else:
        logger.debug('No agent produced output for entry %s', entry_id)
