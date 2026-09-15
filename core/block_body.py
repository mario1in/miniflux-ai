import html
import re

# The model receives the entry as markdown and, when asked to keep the formatting, echoes markdown back:
# image lines, horizontal rules, backslash escapes and [text](url) links. A style_block is plain text
# inside <blockquote><p>, so those have to go or become real HTML before the block is stored.
_MD_IMAGE_RE = re.compile(r'!\[[^\]]*\]\([^)]*\)')
_MD_RULE_RE = re.compile(r'^[ \t]*([-*_])([ \t]*\1){2,}[ \t]*$', re.M)
_MD_ESCAPE_RE = re.compile(r'\\([\\`*_{}\[\]()#+\-.!|>~])')
_MD_LINK_RE = re.compile(r'\[([^\]\n]+)\]\((https?://[^)\s]+)\)')


def block_body(text: str) -> str:
    """LLM output → the inside of a style_block.

    Markdown images and rules are dropped (the original entry below the block still has them), markdown
    escapes are undone, links become <a>, everything else is HTML-escaped and newlines become <br>.
    """
    text = _MD_IMAGE_RE.sub('', text or '')
    text = _MD_RULE_RE.sub('', text)
    text = _MD_ESCAPE_RE.sub(r'\1', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    parts = []
    pos = 0
    for match in _MD_LINK_RE.finditer(text):
        parts.append(html.escape(text[pos:match.start()]))
        parts.append(f'<a href="{html.escape(match.group(2))}">{html.escape(match.group(1))}</a>')
        pos = match.end()
    parts.append(html.escape(text[pos:]))
    return ''.join(parts).replace('\n', '<br>')
