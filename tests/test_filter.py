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
            'content': '<blockquote>\n  <p><strong>🌐 </strong> translated content</p>\n</blockquote><br/>',
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


class TranslationDecisionTest(unittest.TestCase):
    """auto_translate_non_chinese must look at the dominant script, not at the presence of a single Han character."""

    def setUp(self):
        self.agent_config = {
            'title': '🌐 ',
            'style_block': True,
            'auto_translate_non_chinese': True,
            'allow_list': ['https://x.com/*'],
        }
        self.config = DummyConfig(agents={'translate': self.agent_config})
        self.agent = ('translate', self.agent_config)

    def decide(self, title, content):
        entry = {'title': title, 'content': content, 'feed': {'site_url': 'https://x.com/someone'}}
        return filter_entry(self.config, self.agent, entry)

    def test_link_only_post_is_not_translated(self):
        link = 'https://x.com/i/article/2099658876404838400'
        self.assertFalse(self.decide(link, link))

    def test_image_only_post_is_not_translated(self):
        self.assertFalse(self.decide('[图片]', '<img src="https://pbs.twimg.com/media/a.jpg"><br>[图片]'))

    def test_english_post_naming_a_chinese_person_is_translated(self):
        content = ('RT Teortaxes▶️ (DeepSeek 推特🐋铁粉 2023 – ∞)<br>astonishing blogpost from Shengyu Liu (刘胜与, also known as '
                   'interestingLSY/intlsy), kernel engineer at DeepSeek. The first part is his personal struggle with the fact '
                   'that his work is about to render his beloved craft obsolete.<br>永雏塔菲：@teortaxesTex https://mp.weixin.qq.com/s/x')
        self.assertTrue(self.decide(content[:100], content))

    def test_chinese_post_with_english_product_names_is_not_translated(self):
        content = 'Claude Code 的 Agent SDK 今天更新了 Skills 功能，支持 MCP，终于可以在 CI 里跑了。'
        self.assertFalse(self.decide(content, content))

    def test_japanese_post_is_translated(self):
        content = '新しいモデルを公開しました。詳細はブログをご覧ください。'
        self.assertTrue(self.decide(content, content))

    def test_one_word_plus_handle_and_link_is_too_little_to_translate(self):
        self.assertFalse(self.decide('gm @everyone', 'gm @everyone https://t.co/abc'))

    def test_retweet_prefix_and_name_alone_are_not_translated(self):
        self.assertFalse(self.decide('RT Someone', 'RT Someone<br><img src="https://pbs.twimg.com/media/a.jpg">'))

    def test_min_chars_skips_short_posts(self):
        agent_config = {'title': '֎ AI 摘要：', 'style_block': True, 'min_chars': 200}
        config = DummyConfig(agents={'summary': agent_config})
        entry = {'title': 'short', 'content': '<p>' + '字' * 150 + '</p>', 'feed': {'site_url': 'https://weibo.com/u/1'}}
        self.assertFalse(filter_entry(config, ('summary', agent_config), entry))
        entry['content'] = '<p>' + '字' * 250 + '</p>'
        self.assertTrue(filter_entry(config, ('summary', agent_config), entry))


class ScriptProfileTest(unittest.TestCase):
    def test_links_handles_and_tags_do_not_count(self):
        han, kana, words = entry_filter.script_profile('see https://example.com/a-b-c @someone #tag ok')
        self.assertEqual((han, kana, words), (0, 0, 2))

    def test_entities_are_decoded(self):
        self.assertEqual(entry_filter.script_profile('Tom &amp; Jerry'), (0, 0, 2))


if __name__ == '__main__':
    unittest.main()
