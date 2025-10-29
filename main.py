import concurrent.futures
import time

import miniflux
import schedule

from common import Config, get_logger
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

def my_schedule():
    interval = 15 if config.miniflux_webhook_secret else 1
    logger.info('Scheduling unread entry polling every %s minute(s)', interval)
    schedule.every(interval).minutes.do(fetch_unread_entries, config, miniflux_client)
    schedule.run_all()
    logger.info('Initial fetch cycle completed')

    if config.ai_news_schedule:
        feeds = miniflux_client.get_feeds()
        if not any('Newsᴬᴵ for you' in item['title'] for item in feeds):
            try:
                miniflux_client.create_feed(category_id=1, feed_url=config.ai_news_url + '/rss/ai-news')
                logger.info('Created the ai_news feed in Miniflux')
            except Exception as exc:
                logger.error('Failed to create the ai_news feed in Miniflux: %s', exc, exc_info=exc)
        for ai_schedule in config.ai_news_schedule:
            logger.info('Scheduling AI news generation at %s', ai_schedule)
            schedule.every().day.at(ai_schedule).do(generate_daily_news, miniflux_client)

    while True:
        schedule.run_pending()
        time.sleep(1)

def my_flask():
    logger.info('Starting API server on 0.0.0.0:80')
    app.run(host='0.0.0.0', port=80)

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(my_flask)
        executor.submit(my_schedule)
