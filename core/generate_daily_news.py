import json
import time
from textwrap import shorten

from common.config import Config
from common.logger import get_logger
from core.get_ai_result import get_ai_result

config = Config()
logger = get_logger(__name__)


def _preview(text: str) -> str:
    return shorten((text or '').replace('\n', ' ').strip(), width=160, placeholder='…')


def generate_daily_news(miniflux_client):
    logger.info('Generating daily news digest')
    # fetch entries.json
    try:
        with open('entries.json', 'r') as f:
            entries = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning('entries.json missing or empty; skipping AI news generation')
        return []

    if not entries:
        logger.info('No cached summaries available for AI news generation')
        return []

    try:
        contents = '\n'.join([i['content'] for i in entries])
        # greeting
        greeting = get_ai_result(config.ai_news_prompts['greeting'], time.strftime('%B %d, %Y at %I:%M %p'))
        # summary_block
        summary_block = get_ai_result(config.ai_news_prompts['summary_block'], contents)
        # summary
        summary = get_ai_result(config.ai_news_prompts['summary'], summary_block)

        response_content = greeting + '\n\n### 🌐Summary\n' + summary + '\n\n### 📝News\n' + summary_block
        logger.info('Daily news compiled | items=%s | preview="%s"', len(entries), _preview(response_content))

        with open('ai_news.json', 'w') as f:
            json.dump(response_content, f, indent=4, ensure_ascii=False)

        # trigger miniflux feed refresh
        feeds = miniflux_client.get_feeds()
        ai_news_feed_id = next((item['id'] for item in feeds if 'Newsᴬᴵ for you' in item['title']), None)

        if ai_news_feed_id:
            miniflux_client.refresh_feed(ai_news_feed_id)
            logger.debug('Refreshed the ai_news feed in Miniflux | feed_id=%s', ai_news_feed_id)

    except Exception as exc:
        logger.error('Error generating daily news: %s', exc)
        logger.debug('Daily news traceback', exc_info=exc)

    finally:
        try:
            with open('entries.json', 'w') as f:
                json.dump([], f, indent=4, ensure_ascii=False)
            logger.info('Cleared entries.json')
        except Exception as exc:
            logger.error('Failed to clear entries.json: %s', exc)
