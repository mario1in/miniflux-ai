import importlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.entry_filter import filter_entry, is_feed_hidden


class DummyConfig:
    def __init__(self, agents):
        self.agents = agents


def make_entry(hidden_feed=False, hidden_category=False, category='博客', content='<p>Plain English text</p>'):
    return {
        'id': 1,
        'title': 'Example',
        'content': content,
        'feed': {
            'site_url': 'https://example.com',
            'hide_globally': hidden_feed,
            'category': {'title': category, 'hide_globally': hidden_category},
        },
    }


class HiddenFilterTest(unittest.TestCase):
    def test_is_feed_hidden_reads_feed_and_category(self):
        self.assertFalse(is_feed_hidden(make_entry()))
        self.assertTrue(is_feed_hidden(make_entry(hidden_feed=True)))
        self.assertTrue(is_feed_hidden(make_entry(hidden_category=True)))

    def test_skip_hidden_globally(self):
        agent_config = {'title': '֎ AI 摘要：', 'style_block': True, 'skip_hidden_globally': True}
        config = DummyConfig({'summary': agent_config})
        agent = ('summary', agent_config)
        self.assertTrue(filter_entry(config, agent, make_entry()))
        self.assertFalse(filter_entry(config, agent, make_entry(hidden_feed=True)))
        self.assertFalse(filter_entry(config, agent, make_entry(hidden_category=True)))

    def test_category_lists(self):
        deny = {'title': 't', 'style_block': False, 'deny_categories': ['社群']}
        allow = {'title': 't', 'style_block': False, 'allow_categories': ['公众号']}
        self.assertFalse(filter_entry(DummyConfig({'a': deny}), ('a', deny), make_entry(category='社群')))
        self.assertTrue(filter_entry(DummyConfig({'a': deny}), ('a', deny), make_entry(category='博客')))
        self.assertTrue(filter_entry(DummyConfig({'a': allow}), ('a', allow), make_entry(category='公众号')))
        self.assertFalse(filter_entry(DummyConfig({'a': allow}), ('a', allow), make_entry(category='博客')))


class RecordHeadlineTest(unittest.TestCase):
    def setUp(self):
        self.old_cwd = os.getcwd()
        self.tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self.tmpdir.name)
        Path('config.yml').write_text(
            'llm:\n  api_key: dummy\n  base_url: https://example.invalid/v1\n  model: m\n'
            'ai_news:\n  digest_hidden: true\n  headline_hours: 36\nagents: {}\n', encoding='utf8')
        for name in ['common.config', 'core.get_ai_result', 'core.process_entries']:
            sys.modules.pop(name, None)
        self.pe = importlib.import_module('core.process_entries')

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmpdir.cleanup()

    def test_record_dedupes_and_ignores_old_entries(self):
        now = datetime.now(timezone.utc)
        fresh = dict(make_entry(hidden_category=True), id=7, url='https://example.com/7',
                     published_at=(now - timedelta(hours=2)).isoformat())
        stale = dict(make_entry(hidden_category=True), id=8, url='https://example.com/8',
                     published_at=(now - timedelta(hours=72)).isoformat())
        self.assertTrue(self.pe.record_headline(fresh))
        self.assertFalse(self.pe.record_headline(fresh))   # same id again
        self.assertFalse(self.pe.record_headline(stale))   # older than headline_hours
        data = json.loads(Path('entries.json').read_text(encoding='utf8'))
        self.assertEqual([d['id'] for d in data], [7])
        self.assertEqual(data[0]['kind'], 'headline')
        self.assertEqual(data[0]['category'], '博客')


if __name__ == '__main__':
    unittest.main()
