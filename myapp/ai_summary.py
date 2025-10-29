import concurrent.futures
import hashlib
import hmac

import miniflux
from flask import abort, jsonify, request

from common.config import Config
from common.logger import get_logger
from core import process_entry
from myapp import app

config = Config()
miniflux_client = miniflux.Client(config.miniflux_base_url, api_key=config.miniflux_api_key)
logger = get_logger(__name__)


@app.route('/api/miniflux-ai', methods=['POST'])
def miniflux_ai():
    """miniflux Webhook API
    publish new feed entries to this API endpoint
    ---
    post:
      description: Create a random pet
      parameters:
        - in: body
          name: body
          required: True
      responses:
        200:
          content:
            application/json:
              status: string
    """
    payload = request.get_data()
    signature = request.headers.get('X-Miniflux-Signature', '')
    webhook_secret = config.miniflux_webhook_secret

    if webhook_secret:
        computed_signature = hmac.new(webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_signature, signature):
            logger.warning('Rejected webhook with invalid signature')
            abort(403)
    else:
        logger.warning('Webhook secret not configured; skipping signature validation')

    entries_payload = request.json or {}
    entry_items = entries_payload.get('entries', [])
    feed = entries_payload.get('feed', {})

    logger.info(
        'Webhook received | entries=%s | feed="%s"',
        len(entry_items),
        feed.get('title'),
    )

    for entry in entry_items:
        entry['feed'] = feed

    failed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.llm_max_workers) as executor:
        futures = {executor.submit(process_entry, miniflux_client, entry): entry for entry in entry_items}
        for future in concurrent.futures.as_completed(futures):
            entry = futures[future]
            try:
                future.result()
            except Exception as exc:
                failed += 1
                logger.error(
                    'Webhook entry processing failed | entry_id=%s | title="%s"',
                    entry.get('id'),
                    entry.get('title'),
                )
                logger.debug('Webhook entry traceback', exc_info=exc)

    if failed:
        logger.warning('Webhook completed with %s failures', failed)
        return jsonify({'status': 'error', 'failed': failed}), 500

    logger.info('Webhook processed successfully | entries=%s', len(entry_items))
    return jsonify({'status': 'ok'})
