import fnmatch
import html
import re

_TAG_RE = re.compile(r'<[^>]+>')
_URL_RE = re.compile(r'(?:https?://|www\.)\S+')
_HANDLE_RE = re.compile(r'[@#]\w+')
_RT_RE = re.compile(r'^\s*RT\b')                                  # retweet prefix
_CJK_RE = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff]')            # Han ideographs
_KANA_HANGUL_RE = re.compile(r'[\u3040-\u30ff\uac00-\ud7af]')    # Japanese kana, Korean hangul
_WORD_RE = re.compile(r'[^\W\d_]{2,}')                            # runs of letters in any other script

# Fewer words than this and there is nothing to translate (a bare link, an emoji, a single name).
MIN_WORDS_TO_TRANSLATE = 2


def plain_text(value):
    """HTML \u2192 text: tags become spaces, entities are decoded."""
    return html.unescape(_TAG_RE.sub(' ', value or ''))


def script_profile(text):
    """(han, kana_hangul, words): Han characters, kana/hangul characters, and words of any other script.
    Links, @handles and #tags do not count."""
    text = _HANDLE_RE.sub(' ', _URL_RE.sub(' ', _RT_RE.sub(' ', plain_text(text))))
    han = len(_CJK_RE.findall(text))
    kana_hangul = len(_KANA_HANGUL_RE.findall(text))
    words = len(_WORD_RE.findall(_KANA_HANGUL_RE.sub(' ', _CJK_RE.sub(' ', text))))
    return han, kana_hangul, words


def needs_translation(text):
    """True when the text is worth translating into Chinese.

    Japanese and Korean always are. Otherwise the text needs at least MIN_WORDS_TO_TRANSLATE words of a
    non-Han script and Chinese must not already be the dominant script: an English tweet that names a
    Chinese person is translated, a Chinese post that mentions a few English products is not, and a post
    that is only a link or an image is never sent to the model.
    """
    han, kana_hangul, words = script_profile(text)
    if kana_hangul >= 3:
        return True
    if words < MIN_WORDS_TO_TRANSLATE:
        return False
    return han < words


def entry_needs_translation(entry):
    content = entry.get('content') or ''
    if script_profile(content) == (0, 0, 0):   # image-only or link-only post: judge by the title instead
        content = entry.get('title') or ''
    return needs_translation(content)


def entry_length(entry):
    """Visible characters of the content, whitespace excluded (what `min_chars` is compared against)."""
    return len(re.sub(r'\s+', '', plain_text(entry.get('content'))))


# Built-in deny list for internal feeds that should never be processed by any agent
BUILTIN_DENY_LIST = [
    'https://ai-news.miniflux',
    'https://feeds-status.miniflux',
]

def is_feed_hidden(entry):
    """True when the feed, or its category, is marked "hide globally" in Miniflux."""
    feed = entry.get('feed') or {}
    if feed.get('hide_globally'):
        return True
    return bool((feed.get('category') or {}).get('hide_globally'))


def category_title(entry):
    return ((entry.get('feed') or {}).get('category') or {}).get('title') or ''


def filter_entry(config, agent, entry):
    start_with_list = [a.get('title', '') for a in config.agents.values()]
    style_block = [a.get('style_block') for a in config.agents.values()]
    [start_with_list.append('<blockquote>') for i in style_block if i]

    # Todo Compatible with whitelist/blacklist parameter, to be removed
    agent_config = agent[1]
    allow_list = agent_config.get('allow_list') if agent_config.get('allow_list') is not None else agent_config.get('whitelist')
    deny_list = agent_config['deny_list'] if agent_config.get('deny_list') is not None else agent_config.get('blacklist')
    auto_translate_non_chinese = agent_config.get('auto_translate_non_chinese', False)

    site_url = (entry.get('feed') or {}).get('site_url', '')
    entry_id = entry.get('id')

    # Always block internal URLs regardless of agent config
    if any(fnmatch.fnmatch(entry['feed']['site_url'], pattern) for pattern in BUILTIN_DENY_LIST):
        return False

    # filter, if not content starts with start flag
    if not entry['content'].startswith(tuple(start_with_list)):
        # feeds/categories marked "hide globally" in Miniflux (泛读) can be excluded per agent
        if agent_config.get('skip_hidden_globally') and is_feed_hidden(entry):
            return False
        allow_categories = agent_config.get('allow_categories')
        deny_categories = agent_config.get('deny_categories')
        title_of_category = category_title(entry)
        if allow_categories is not None and title_of_category not in allow_categories:
            return False
        if deny_categories and title_of_category in deny_categories:
            return False
        # short posts are not worth a model call (per agent, in visible characters)
        min_chars = agent_config.get('min_chars') or 0
        if min_chars and entry_length(entry) < min_chars:
            return False

        wants_translation = entry_needs_translation(entry) if auto_translate_non_chinese else True

        # filter, if in allow_list
        if allow_list is not None:
            matched_pattern = next((pattern for pattern in allow_list if fnmatch.fnmatch(site_url, pattern)), None)
            if matched_pattern:
                return wants_translation
            return False

        # filter, if not in deny_list
        elif deny_list is not None:
            matched_pattern = next((pattern for pattern in deny_list if fnmatch.fnmatch(site_url, pattern)), None)
            if matched_pattern:
                return False
            return wants_translation

        # filter, if allow_list and deny_list are both None
        elif allow_list is None and deny_list is None:
            return wants_translation

    return False
