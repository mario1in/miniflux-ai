import concurrent.futures
import time

from common.logger import get_logger
from core.process_entries import process_entry

logger = get_logger(__name__)

# Miniflux >= 2.3 rejects limit values above 1000
ENTRY_LIMIT = 1000


def fetch_unread_entries(config, miniflux_client):
    start_time = time.time()
    logger.info('Task fetch_unread_entries started')
    try:
        entries = miniflux_client.get_entries(
            status=['unread'], limit=ENTRY_LIMIT, order='published_at', direction='desc'
        )
    except Exception as exc:
        logger.error('Failed to fetch unread entries from Miniflux: %s', exc)
        logger.debug('Fetch traceback', exc_info=exc)
        return

    unread_entries = entries.get('entries', [])
    total = len(unread_entries)

    if total == 0:
        logger.info('No unread entries found')
        return

    logger.info('Fetched %s unread entries (limit=%s)', total, ENTRY_LIMIT)
    processed = 0
    failed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=config.llm_max_workers) as executor:
        futures = {executor.submit(process_entry, miniflux_client, entry): entry for entry in unread_entries}
        for future in concurrent.futures.as_completed(futures):
            entry = futures[future]
            try:
                future.result()
                processed += 1
            except Exception as exc:
                failed += 1
                entry_title = entry.get('title', 'unknown')
                logger.error('Entry processing failed | title="%s" | id=%s', entry_title, entry.get('id'))
                logger.debug('Entry processing traceback', exc_info=exc)

    duration = time.time() - start_time
    logger.info(
        'Task fetch_unread_entries finished | processed=%s | failed=%s | duration=%.2fs',
        processed,
        failed,
        duration,
    )
