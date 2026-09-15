import os
from pathlib import Path

# Where the runtime state lives: the digest buffer (entries.json), the generated digest (ai_news.json) and
# feeds_status.json. Defaults to the working directory, as before; point DATA_DIR at a persistent volume on
# platforms whose containers start from a clean image on every deploy, so a redeploy no longer empties the
# digest buffer.


def data_dir() -> Path:
    directory = Path(os.environ.get('DATA_DIR') or '.')
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def data_path(name: str) -> Path:
    return data_dir() / name
