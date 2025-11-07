import unittest
from types import SimpleNamespace
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRY_FILTER_PATH = PROJECT_ROOT / 'core' / 'entry_filter.py'

spec = importlib.util.spec_from_file_location('core.entry_filter', ENTRY_FILTER_PATH)
entry_filter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry_filter)
filter_entry = entry_filter.filter_entry


class DummyConfig(SimpleNamespace):
    pass


class FilterEntryTest(unittest.TestCase):
    def test_skip_when_content_already_processed_with_style_block(self):
        agent_config = {
            'title': '🌐AI 翻译',
            'style_block': True
        }
        config = DummyConfig(agents={'translate': agent_config})
        agent = ('translate', agent_config)
        entry = {
            'title': 'Example',
            'content': '<pre translated content',
            'feed': {'site_url': 'https://example.com'}
        }

        self.assertFalse(filter_entry(config, agent, entry))

    def test_allow_list_matches(self):
        agent_config = {
            'title': '🌐AI 翻译',
            'style_block': False,
            'allow_list': ['https://allowed.com/*']
        }
        config = DummyConfig(agents={'translate': agent_config})
        agent = ('translate', agent_config)
        entry = {
            'title': 'Example',
            'content': 'New article',
            'feed': {'site_url': 'https://allowed.com/news'}
        }

        self.assertTrue(filter_entry(config, agent, entry))

    def test_deny_list_blocks(self):
        agent_config = {
            'title': '🌐AI 翻译',
            'style_block': False,
            'deny_list': ['https://blocked.com/*']
        }
        config = DummyConfig(agents={'translate': agent_config})
        agent = ('translate', agent_config)
        entry = {
            'title': 'Example',
            'content': 'Content to skip',
            'feed': {'site_url': 'https://blocked.com/post'}
        }

        self.assertFalse(filter_entry(config, agent, entry))

    def test_auto_translate_for_non_chinese_content(self):
        agent_config = {
            'title': '🌐AI translate: ',
            'style_block': False,
            'auto_translate_non_chinese': True
        }
        config = DummyConfig(agents={'translate': agent_config})
        agent = ('translate', agent_config)
        entry = {
            'title': 'Breaking News',
            'content': '<p>Hello world</p>',
            'feed': {'site_url': 'https://news.com/article'}
        }

        self.assertTrue(filter_entry(config, agent, entry))

    def test_auto_translate_skips_chinese_content(self):
        agent_config = {
            'title': '🌐AI translate: ',
            'style_block': False,
            'auto_translate_non_chinese': True
        }
        config = DummyConfig(agents={'translate': agent_config})
        agent = ('translate', agent_config)
        entry = {
            'title': '国内新闻',
            'content': '<p>这是一个测试</p>',
            'feed': {'site_url': 'https://news.cn/article'}
        }

        self.assertFalse(filter_entry(config, agent, entry))

    def test_auto_translate_respects_allow_list_for_non_match(self):
        agent_config = {
            'title': '🌐AI translate: ',
            'style_block': False,
            'auto_translate_non_chinese': True,
            'allow_list': ['https://twitterapi.zeabur.app/*']
        }
        config = DummyConfig(agents={'translate': agent_config})
        agent = ('translate', agent_config)
        entry = {
            'title': 'Other feed',
            'content': '<p>Hello world</p>',
            'feed': {'site_url': 'https://example.com/post'}
        }

        self.assertFalse(filter_entry(config, agent, entry))

    def test_auto_translate_allow_list_skips_chinese_content(self):
        agent_config = {
            'title': '🌐AI translate: ',
            'style_block': False,
            'auto_translate_non_chinese': True,
            'allow_list': ['https://twitterapi.zeabur.app/*']
        }
        config = DummyConfig(agents={'translate': agent_config})
        agent = ('translate', agent_config)
        entry = {
            'title': '国内新闻',
            'content': '<p>这是一个测试</p>',
            'feed': {'site_url': 'https://twitterapi.zeabur.app/feed'}
        }

        self.assertFalse(filter_entry(config, agent, entry))

    def test_auto_translate_allow_list_allows_non_chinese_match(self):
        agent_config = {
            'title': '🌐AI translate: ',
            'style_block': False,
            'auto_translate_non_chinese': True,
            'allow_list': ['https://twitterapi.zeabur.app/*']
        }
        config = DummyConfig(agents={'translate': agent_config})
        agent = ('translate', agent_config)
        entry = {
            'title': 'Hello',
            'content': '<p>Hello world</p>',
            'feed': {'site_url': 'https://twitterapi.zeabur.app/feed'}
        }

        self.assertTrue(filter_entry(config, agent, entry))


if __name__ == '__main__':
    unittest.main()
