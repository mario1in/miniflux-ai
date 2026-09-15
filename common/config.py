import os

from yaml import safe_load

# Secrets and connection settings can be supplied as environment variables so that
# config.yml never has to contain credentials. An environment variable wins over
# the value in config.yml; empty variables are ignored.
ENV_OVERRIDES = {
    ('miniflux', 'base_url'): 'MINIFLUX_BASE_URL',
    ('miniflux', 'api_key'): 'MINIFLUX_API_KEY',
    ('miniflux', 'webhook_secret'): 'MINIFLUX_WEBHOOK_SECRET',
    ('llm', 'provider'): 'LLM_PROVIDER',
    ('llm', 'base_url'): 'LLM_BASE_URL',
    ('llm', 'api_key'): 'LLM_API_KEY',
    ('llm', 'model'): 'LLM_MODEL',
    ('ai_news', 'url'): 'AI_NEWS_URL',
}


class Config:
    def __init__(self):
        config_path = os.environ.get('CONFIG_PATH', 'config.yml')
        with open(config_path, encoding='utf8') as config_file:
            self.c = safe_load(config_file) or {}
        self.log_level = self.c.get('log_level', 'INFO')

        self.miniflux_base_url = self.get_config_value('miniflux', 'base_url', None)
        self.miniflux_api_key = self.get_config_value('miniflux', 'api_key', None)
        self.miniflux_webhook_secret = self.get_config_value('miniflux', 'webhook_secret', None)
        self.miniflux_schedule_interval = self.get_config_value('miniflux', 'schedule_interval', None)

        self.llm_provider = self.get_config_value('llm', 'provider', 'openai')
        self.llm_base_url = self.get_config_value('llm', 'base_url', None)
        self.llm_api_key = self.get_config_value('llm', 'api_key', None)
        self.llm_model = self.get_config_value('llm', 'model', None)
        self.llm_max_length = self.get_config_value('llm', 'max_length', None)
        self.llm_timeout = self.get_config_value('llm', 'timeout', 60)
        self.llm_max_workers = self.get_config_value('llm', 'max_workers', 4)
        self.llm_RPM = self.get_config_value('llm', 'RPM', 1000)
        self.llm_extra_params = self.get_config_value('llm', 'extra_params', {})
        if self.llm_extra_params is None:
            self.llm_extra_params = {}
        if not isinstance(self.llm_extra_params, dict):
            raise ValueError('llm.extra_params must be a mapping')

        self.ai_news_url = self.get_config_value('ai_news', 'url', None)
        self.ai_news_schedule = self.get_config_value('ai_news', 'schedule', None)
        self.ai_news_prompts = self.get_config_value('ai_news', 'prompts', None)
        # collect titles of entries from hidden-globally feeds for a once-a-day digest (no per-entry LLM call)
        self.ai_news_digest_hidden = self.get_config_value('ai_news', 'digest_hidden', False)
        self.ai_news_headline_hours = self.get_config_value('ai_news', 'headline_hours', 36)
        self.ai_news_headline_limit = self.get_config_value('ai_news', 'headline_limit', 150)

        self.feeds_status_enabled = self.get_config_value('feeds_status', 'enabled', False)
        self.feeds_status_url = self.get_config_value('feeds_status', 'url', self.ai_news_url)
        self.feeds_status_schedule = self.get_config_value('feeds_status', 'schedule', '09:00')

        self.agents = self.c.get('agents', {})

    def get_config_value(self, section, key, default=None):
        env_name = ENV_OVERRIDES.get((section, key))
        if env_name:
            env_value = os.environ.get(env_name)
            if env_value not in (None, ''):
                return env_value
        section_values = self.c.get(section) or {}
        return section_values.get(key, default)
