import importlib.util
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('core.feed_info', PROJECT_ROOT / 'core' / 'feed_info.py')
feed_info = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed_info)


class FullFeedTest(unittest.TestCase):
    def setUp(self):
        feed_info.clear_cache()
        self.webhook_feed = {'id': 42, 'title': '歸藏的即刻动态', 'site_url': 'https://okjike.com/u/1'}
        self.api_feed = {'id': 42, 'title': '歸藏的即刻动态', 'hide_globally': False,
                         'category': {'id': 5, 'title': '即刻', 'hide_globally': False}}

    def test_completes_the_webhook_feed_and_caches_it(self):
        client = mock.Mock()
        client.get_feed.return_value = self.api_feed
        first = feed_info.full_feed(client, self.webhook_feed)
        second = feed_info.full_feed(client, self.webhook_feed)
        self.assertEqual(first['category']['title'], '即刻')
        self.assertEqual(first['site_url'], 'https://okjike.com/u/1')
        self.assertEqual(second, first)
        client.get_feed.assert_called_once_with(42)

    def test_expired_cache_is_refreshed(self):
        client = mock.Mock()
        client.get_feed.return_value = self.api_feed
        feed_info.full_feed(client, self.webhook_feed)
        feed_info.full_feed(client, self.webhook_feed, cache_seconds=0)
        self.assertEqual(client.get_feed.call_count, 2)

    def test_lookup_failure_keeps_the_webhook_feed(self):
        client = mock.Mock()
        client.get_feed.side_effect = RuntimeError('boom')
        self.assertEqual(feed_info.full_feed(client, self.webhook_feed), self.webhook_feed)
        self.assertEqual(feed_info.full_feed(mock.Mock(), {}), {})


if __name__ == '__main__':
    unittest.main()
