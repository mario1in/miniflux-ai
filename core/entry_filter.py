import fnmatch
import re

_CJK_PATTERN = re.compile(r'[\u4e00-\u9fff]')

def _extract_plain_text(entry):
    content = entry.get('content') or ''
    title = entry.get('title') or ''
    raw_text = f"{title}\n{content}"
    return re.sub(r'<[^>]+>', ' ', raw_text)


def _contains_cjk(text):
    return bool(_CJK_PATTERN.search(text))


def filter_entry(config, agent, entry):
    start_with_list = [name[1]['title'] for name in config.agents.items()]
    style_block = [name[1]['style_block'] for name in config.agents.items()]
    [start_with_list.append('<pre') for i in style_block if i]

    # Todo Compatible with whitelist/blacklist parameter, to be removed
    agent_config = agent[1]
    allow_list = agent_config.get('allow_list') if agent_config.get('allow_list') is not None else agent_config.get('whitelist')
    deny_list = agent_config['deny_list'] if agent_config.get('deny_list') is not None else agent_config.get('blacklist')
    auto_translate_non_chinese = agent_config.get('auto_translate_non_chinese', False)

    site_url = (entry.get('feed') or {}).get('site_url', '')
    entry_id = entry.get('id')

    # filter, if not content starts with start flag
    if not entry['content'].startswith(tuple(start_with_list)):
        plain_text = _extract_plain_text(entry)
        has_cjk = _contains_cjk(plain_text)

        # filter, if in allow_list
        if allow_list is not None:
            matched_pattern = next((pattern for pattern in allow_list if fnmatch.fnmatch(site_url, pattern)), None)
            if matched_pattern:
                if auto_translate_non_chinese:
                    decision = not has_cjk
                    return decision
                return True
            return False

        # filter, if not in deny_list
        elif deny_list is not None:
            matched_pattern = next((pattern for pattern in deny_list if fnmatch.fnmatch(site_url, pattern)), None)
            if matched_pattern:
                return False
            if auto_translate_non_chinese:
                decision = not has_cjk
                return decision
            return True

        # filter, if allow_list and deny_list are both None
        elif allow_list is None and deny_list is None:
            if auto_translate_non_chinese:
                decision = not has_cjk
                return decision
            return True

    return False
