import json
from datetime import datetime
import time

import markdown
from openai import OpenAI
from feedgen.feed import FeedGenerator

from common.config import Config
from common.logger import get_logger
from myapp import app

config = Config()
llm_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)
logger = get_logger(__name__)

@app.route('/rss/ai-news', methods=['GET'])
def miniflux_ai_news():
    """miniflux Webhook API
    publish new feed entries to this API endpoint
    ---
    get:
      description: Get rss feed
      responses:
        200:
          content:
            application/json:
              status: string
    """
    # Todo 根据需要获取最近时间内的文章，或总结后的列表
    logger.info('Serving AI news RSS request')
    try:
        with open('ai_news.json', 'r') as file:
            ai_news = json.load(file)
    except FileNotFoundError:
        ai_news = ''
        logger.warning('ai_news.json not found; returning welcome placeholder')
    except Exception as exc:
        logger.error('Failed to read ai_news.json', exc_info=exc)
        ai_news = ''

    # 清空 ai_news.json
    with open('ai_news.json', 'w') as file:
        json.dump('', file, indent=4, ensure_ascii=False)


    fg = FeedGenerator()
    fg.id('https://ai-news.miniflux')
    fg.title('֎Newsᴬᴵ for you')
    fg.subtitle('Powered by miniflux-ai')
    fg.author({'name': 'miniflux-ai'})
    fg.link(href='https://ai-news.miniflux', rel='self')

    fe_welcome = fg.add_entry()
    fe_welcome.id('https://ai-news.miniflux')
    fe_welcome.link(href='https://ai-news.miniflux')
    fe_welcome.title(f"Welcome to Newsᴬᴵ")
    fe_welcome.description(markdown.markdown('Welcome to Newsᴬᴵ'))

    if ai_news:
        fe = fg.add_entry()
        fe.id('https://ai-news.miniflux' + time.strftime('%Y-%m-%d-%H-%M'))
        fe.link(href='https://ai-news.miniflux' + time.strftime('%Y-%m-%d-%H-%M'))
        fe.title(f"{'Morning' if datetime.today().hour < 12 else 'Nightly'} Newsᴬᴵ for you - {time.strftime('%Y-%m-%d')}")
        fe.description(markdown.markdown(ai_news))
        logger.info('Published AI news entry | timestamp=%s', time.strftime('%Y-%m-%d-%H-%M'))
    else:
        logger.debug('No AI news content available; responding with welcome feed only')

    result = fg.rss_str(pretty=True)
    return result
