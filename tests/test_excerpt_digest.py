import importlib
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def make_entry(entry_id, category, title, content, hidden=False):
    return {
        'id': entry_id,
        'title': title,
        'content': content,
        'url': f'https://example.com/{entry_id}',
        'published_at': (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        'feed': {'site_url': 'https://example.com', 'hide_globally': hidden,
                 'category': {'title': category, 'hide_globally': False}},
    }


class ExcerptDigestTest(unittest.TestCase):
    """Categories in ai_news.excerpt_categories reach the digest without a per-entry summary."""

    def setUp(self):
        self.old_cwd = os.getcwd()
        self.tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self.tmpdir.name)
        Path('config.yml').write_text(
            'llm:\n  api_key: dummy\n  base_url: https://example.invalid/v1\n  model: m\n'
            'ai_news:\n  digest_hidden: true\n  excerpt_categories: [微博, 即刻]\n  excerpt_chars: 40\n  excerpt_limit: 2\n'
            '  prompts:\n    greeting: g\n    summary: s\n    summary_block: b\n    headlines: h\n'
            'agents: {}\n', encoding='utf8')
        for name in ['common.config', 'core.get_ai_result', 'core.process_entries', 'core.generate_daily_news']:
            sys.modules.pop(name, None)
        self.pe = importlib.import_module('core.process_entries')
        self.gd = importlib.import_module('core.generate_daily_news')

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmpdir.cleanup()

    def test_excerpt_of_prefixes_title_only_when_needed(self):
        social = make_entry(1, '微博', '宝玉xp: 有传闻说 Opus 5.2 在灰度', '<p>宝玉xp: 有传闻说 Opus 5.2 在灰度，图1据说是 Opus 5.2 生成的，我测试了一下，似乎并没有</p>')
        self.assertTrue(self.pe.excerpt_of(social, 40).startswith('宝玉xp: 有传闻说'))
        self.assertNotIn('：宝玉xp', self.pe.excerpt_of(social, 40))
        article = make_entry(2, '博客', '一个标题', '<p>正文和标题不一样</p>')
        self.assertEqual(self.pe.excerpt_of(article, 40), '一个标题：正文和标题不一样')
        self.assertEqual(self.pe.excerpt_of(make_entry(3, '博客', '只有标题', ''), 40), '只有标题')

    def test_process_entry_records_excerpt_instead_of_calling_the_model(self):
        with mock.patch.object(self.pe, 'get_ai_result') as ai:
            entry = make_entry(5, '即刻', '发布了: 卧槽！我开发的应用上架了', '<p>发布了: 卧槽！我开发的应用上架了，目前限免。</p>')
            self.pe.process_entry(mock.Mock(), entry)
            ai.assert_not_called()
        data = json.loads(Path('entries.json').read_text(encoding='utf8'))
        self.assertEqual([(d['kind'], d['id']) for d in data], [('excerpt', 5)])
        self.assertTrue(data[0]['content'].startswith('发布了: 卧槽'))

    def test_daily_news_feeds_excerpts_into_the_news_list(self):
        for i, text in enumerate(['第一条', '第二条', '第三条'], start=1):
            self.pe.record_excerpt(make_entry(i, '微博', text, f'<p>{text}正文</p>'))
        seen = {}

        def fake_ai(prompt, request):
            seen[prompt] = request
            return f'<{prompt}>'

        with mock.patch.object(self.gd, 'get_ai_result', side_effect=fake_ai):
            client = mock.Mock()
            client.get_feeds.return_value = []
            self.gd.generate_daily_news(client)
        # excerpt_limit: 2 keeps the newest two
        self.assertEqual(seen['b'], '第二条正文\n第三条正文')
        self.assertIn('### 📝News', json.loads(Path('ai_news.json').read_text(encoding='utf8')))
        self.assertEqual(json.loads(Path('entries.json').read_text(encoding='utf8')), [])


if __name__ == '__main__':
    unittest.main()
