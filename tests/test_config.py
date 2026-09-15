import importlib.util
import os
import tempfile
import unittest
from pathlib import Path


def load_config_class():
    config_path = Path(__file__).resolve().parents[1] / "common" / "config.py"
    spec = importlib.util.spec_from_file_location("config_mod", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Config


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.Config = load_config_class()
        self.old_cwd = os.getcwd()
        self.tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self.tmpdir.name)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmpdir.cleanup()

    def write_config(self, content):
        Path("config.yml").write_text(content, encoding="utf8")

    def test_extra_params_defaults_to_empty_mapping(self):
        self.write_config("llm:\n  extra_params:\n")

        config = self.Config()

        self.assertEqual(config.llm_extra_params, {})

    def test_extra_params_accepts_nested_mapping(self):
        self.write_config(
            "llm:\n"
            "  extra_params:\n"
            "    thinking_config:\n"
            "      thinking_budget: 0\n"
        )

        config = self.Config()

        self.assertEqual(
            config.llm_extra_params,
            {"thinking_config": {"thinking_budget": 0}},
        )

    def test_extra_params_rejects_non_mapping(self):
        self.write_config("llm:\n  extra_params: nope\n")

        with self.assertRaises(ValueError):
            self.Config()


    def test_env_overrides_config_file_values(self):
        self.write_config(
            "miniflux:\n"
            "  base_url: https://file.example\n"
            "  api_key: file-key\n"
            "llm:\n"
            "  base_url: https://llm.file.example\n"
            "  api_key: file-llm-key\n"
            "  model: file-model\n"
        )
        overrides = {
            "MINIFLUX_API_KEY": "env-key",
            "LLM_API_KEY": "env-llm-key",
            "LLM_MODEL": "env-model",
            "LLM_BASE_URL": "",  # empty values must not override
        }
        saved = {k: os.environ.get(k) for k in overrides}
        os.environ.update(overrides)
        try:
            config = self.Config()
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        self.assertEqual(config.miniflux_api_key, "env-key")
        self.assertEqual(config.miniflux_base_url, "https://file.example")
        self.assertEqual(config.llm_api_key, "env-llm-key")
        self.assertEqual(config.llm_model, "env-model")
        self.assertEqual(config.llm_base_url, "https://llm.file.example")

    def test_missing_section_is_tolerated(self):
        self.write_config("log_level: INFO\n")

        config = self.Config()

        self.assertIsNone(config.llm_api_key)
        self.assertEqual(config.llm_timeout, 60)


if __name__ == "__main__":
    unittest.main()
