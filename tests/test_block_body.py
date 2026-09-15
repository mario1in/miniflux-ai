import importlib.util
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('core.block_body', PROJECT_ROOT / 'core' / 'block_body.py')
block_body_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(block_body_module)
block_body = block_body_module.block_body


class BlockBodyTest(unittest.TestCase):
    def test_markdown_images_and_rules_are_dropped(self):
        text = ('好吧。只能说我们同意。\n\n'
                '![](https://pbs.twimg.com/media/a?format=png&name=orig)  \n'
                '![](https://pbs.twimg.com/media/b?format=png&name=orig)\n\n'
                '---\n\n'
                '永雏塔菲： @teortaxesTex')
        self.assertEqual(block_body(text), '好吧。只能说我们同意。<br><br>永雏塔菲： @teortaxesTex')

    def test_markdown_escapes_are_undone_and_html_is_escaped(self):
        self.assertEqual(block_body(r'看 mp.weixin.qq.com/s/zk0K\_OHMA & <b>粗体</b>'),
                         '看 mp.weixin.qq.com/s/zk0K_OHMA &amp; &lt;b&gt;粗体&lt;/b&gt;')

    def test_markdown_links_become_anchors(self):
        self.assertEqual(block_body('详见 [博客](https://example.com/a?b=1&c=2) 一文'),
                         '详见 <a href="https://example.com/a?b=1&amp;c=2">博客</a> 一文')

    def test_newlines_become_breaks_and_blank_runs_collapse(self):
        self.assertEqual(block_body('一\n\n\n\n二  \n三'), '一<br><br>二<br>三')

    def test_empty_output(self):
        self.assertEqual(block_body(None), '')


if __name__ == '__main__':
    unittest.main()
