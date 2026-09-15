import concurrent.futures
import os
import time
import traceback

import miniflux
import schedule

from common import Config, get_logger
from services.feeds_status_service import ensure_miniflux_feed, generate_feeds_status, resolve_feeds_status_url
from myapp import app
from core import fetch_unread_entries, generate_daily_news

logger = get_logger(__name__)

config = Config()
miniflux_client = miniflux.Client(config.miniflux_base_url, api_key=config.miniflux_api_key)
logger.info('Bootstrapping miniflux-ai workers')
attempt = 0

while True:
    attempt += 1
    try:
        logger.info('Connecting to Miniflux (attempt %s)', attempt)
        alive = miniflux_client.me()
        username = alive.get('username') if isinstance(alive, dict) else 'unknown'
        logger.info('Successfully connected to Miniflux as %s', username)
        break
    except Exception as exc:
        logger.warning('Cannot connect to Miniflux (attempt %s failed): %s', attempt, exc)
        logger.debug('Miniflux connection traceback', exc_info=exc)
        time.sleep(3)


def resolve_ai_news_url():
    if not config.ai_news_url:
        return None
    return config.ai_news_url.rstrip('/') + '/rss/ai-news'


def my_schedule():
    if config.miniflux_schedule_interval:
        interval = config.miniflux_schedule_interval
    else:
        interval = 15 if config.miniflux_webhook_secret else 1
    logger.info('Scheduling unread entry polling every %s minute(s)', interval)
    schedule.every(interval).minutes.do(fetch_unread_entries, config, miniflux_client)
    try:
        schedule.run_all()
    except Exception as exc:
        logger.error('Initial fetch cycle failed: %s', exc)
        logger.error(traceback.format_exc())
    logger.info('Initial fetch cycle completed')

    if config.ai_news_schedule:
        try:
            ensure_miniflux_feed(miniflux_client, resolve_ai_news_url(), 'ai_news')
        except Exception as exc:
            logger.error('Failed to ensure the ai_news feed in Miniflux: %s', exc)
        for ai_schedule in config.ai_news_schedule:
            schedule.every().day.at(ai_schedule).do(generate_daily_news, miniflux_client)
            logger.info('Scheduled AI news generation at %s', ai_schedule)

    if config.feeds_status_enabled:
        try:
            ensure_miniflux_feed(miniflux_client, resolve_feeds_status_url(config.feeds_status_url), 'feeds_status')
        except Exception as exc:
            logger.error('Failed to ensure the feeds_status feed in Miniflux: %s', exc)
        schedule.every().day.at(config.feeds_status_schedule).do(
            generate_feeds_status,
            miniflux_client,
            config.feeds_status_url,
        )
        logger.info('Scheduled feeds_status generation at %s', config.feeds_status_schedule)

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as exc:
            logger.error('An error occurred in the schedule loop: %s', exc)
            logger.error(traceback.format_exc())
            time.sleep(30)


def my_flask():
    # Honor the platform-provided PORT (Zeabur/Heroku style); default to 80 for docker-compose setups
    port = int(os.environ.get('PORT', 80))
    logger.info('Starting API server on 0.0.0.0:%s', port)
    app.run(host='0.0.0.0', port=port)


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        if config.ai_news_schedule or config.miniflux_webhook_secret or config.feeds_status_enabled:
            executor.submit(my_flask)
        executor.submit(my_schedule)
