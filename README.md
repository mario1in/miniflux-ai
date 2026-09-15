# miniflux-ai

Miniflux with AI

This project integrates with Miniflux to fetch RSS feed content via API or webhook. It then utilizes large language models (e.g., Ollama, ChatGPT, LLaMA, Gemini) to generate summaries, translations, and AI-driven news insights.

## Features

- **Miniflux Integration**: Seamlessly fetch unread entries from Miniflux or trigger via webhook.
- **Schedule Interval**: Specifies the time interval for requesting the miniflux api.
- **LLM Processing**: Generate summaries, translations, etc. based on your chosen LLM agent.
- **AI News**: Use the LLM agent to generate AI morning and evening news from feed content.
- **Flexible Configuration**: Easily modify or add new agents via the `config.yml` file.
- **Markdown and HTML Support**: Outputs in Markdown or styled HTML blocks, depending on configuration.

<table>
  <tr>
    <td>
      summaries, translations
    </td>
    <td>
      AI News
    </td> 
  </tr>
  <tr>
    <td> 
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="https://github.com/user-attachments/assets/11c208d9-816a-4c8c-bc00-2f780529e58d">
        <source media="(prefers-color-scheme: light)" srcset="https://github.com/user-attachments/assets/c97e2774-ec10-4acb-bef7-25cf8d43da15">
        <img alt="miniflux AI summaries translations" src="https://github.com/user-attachments/assets/c97e2774-ec10-4acb-bef7-25cf8d43da15" width="400" > 
      </picture>
    </td>
    <td> 
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="https://github.com/user-attachments/assets/b40f5bdd-d265-4beb-a14c-d39d6624760b">
        <source media="(prefers-color-scheme: light)" srcset="https://github.com/user-attachments/assets/e5985025-15f3-43b0-982b-422575962783">
        <img alt="miniflux AI summaries translations" src="https://github.com/user-attachments/assets/e5985025-15f3-43b0-982b-422575962783" width="400" > 
      </picture>
    </td>
  </tr>
</table>


### Environment variable overrides

Credentials do not have to live in `config.yml`. The following environment variables take precedence over the file (empty values are ignored): `MINIFLUX_BASE_URL`, `MINIFLUX_API_KEY`, `MINIFLUX_WEBHOOK_SECRET`, `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`. `CONFIG_PATH` selects a different config file. The API server listens on `PORT` when it is set (default 80).


### 精读 / 泛读 (hidden-globally feeds)

Feeds or categories marked **hide globally** in Miniflux are treated as "泛读" (skim). Per agent, `skip_hidden_globally: true` skips them, and `allow_categories` / `deny_categories` filter by Miniflux category title. With `ai_news.digest_hidden: true` their titles and links are collected (no LLM call) and summarised once per digest using the `ai_news.prompts.headlines` prompt; `headline_hours` / `headline_limit` bound the collected list. `AI_NEWS_URL` overrides `ai_news.url`.

## Requirements

- Python 3.11+
- Dependencies: Install via `pip install -r requirements.txt`
- Miniflux API Key
- API Key compatible with OpenAI-compatible LLMs (e.g., Ollama for LLaMA 3.1)

## Configuration

The repository includes a template configuration file: `config.sample.yml`. Modify the `config.yml` to set up:

> If using a webhook, enter the URL in Settings > Integrations > Webhook > Webhook URL.
>
> If deploying in a container alongside Miniflux, use the following URL:
> http://miniflux_ai/api/miniflux-ai.

- **Miniflux**: Base URL and API key.
- **LLM**: Model settings, API key, and endpoint.Add timeout, max_workers parameters due to multithreading
- **AI News**: Schedule and prompts for daily news generation
- **Agents**: Define each agent's prompt, allow_list/deny_list filters, and output style（`style_block` parameter controls whether the output is formatted as a code block in Markdown）。You can also enable behaviors such as auto-translating non-Chinese content via `auto_translate_non_chinese`.
  - `auto_translate_non_chinese` looks at the dominant script of the post (links, @handles and #tags ignored): Japanese/Korean is always translated; other text needs at least 3 words of a non-Han script and fewer Han characters than words. An English tweet that names a Chinese person is translated, a Chinese post that mentions a few English products is not, and a post that is only a link or an image is never sent to the model.
  - `min_chars`: skip posts with fewer visible characters than this (per agent), e.g. `min_chars: 200` on a summary agent avoids summarising one-line posts.
- **Persistent state**: `entries.json` (digest buffer), `ai_news.json` and `feeds_status.json` are written to the working directory by default. Set `DATA_DIR` (e.g. `/data`) to a mounted volume on platforms that rebuild the container from a clean image on every deploy, otherwise each deploy empties the digest buffer.
- **AI News without a per-entry summary**: the digest's news list is built from the `summary` agent's output, so a category the agent skips (`deny_categories`) would vanish from the digest. List such categories under `ai_news.excerpt_categories` and their entries reach the digest as the opening `excerpt_chars` characters of the post (default 120, newest `excerpt_limit` entries, default 80) with no model call.

## Docker Setup

The project includes a `docker-compose.yml` file for easy deployment:

> If using webhook or AI news, it is recommended to use the same docker-compose.yml with miniflux and access it via container name.

```yaml
services:
  miniflux_ai:
    container_name: miniflux_ai
    image: ghcr.io/qetesh/miniflux-ai:latest
    restart: always
    environment:
      TZ: Asia/Shanghai
    volumes:
      - ./config.yml:/app/config.yml
      # - ./entries.json:/app/entries.json # Provide persistent for AI news
```

Refer to `config.sample.*.yml`, create `config.yml`
To start the services:

```bash
docker-compose up -d
```

## Usage

1. Ensure `config.yml` is properly configured.
2. Run the script: `python main.py`
3. The script will fetch unread RSS entries, process them with the LLM, and update the content in Miniflux.

## Roadmap

- [x] Add daily summary(by title, Summary of existing AI)
  - [x] Add Morning and Evening News（e.g. 9/24: AI Morning News, 9/24: AI Evening News）
  - [x] Add timed summary

## FAQ

<details>
<summary> If the formatting of summary content is incorrect, add the following code in Settings > Custom CSS: </summary>

```
pre code {
    white-space: pre-wrap;
    word-wrap: break-word;
}
```
</details>

<details>
<summary> fetcher: refusing to access private network host "xx.xx.xx.xx" </summary>

Starting with Miniflux 2.2.18, `FETCHER_ALLOW_PRIVATE_NETWORKS=1` must now be enabled to access feeds hosted on a local network. See the [official release notes](https://github.com/miniflux/v2/releases/tag/2.2.18) for details.

</details>

<details>
<summary> level=WARN msg="Unable to send new entries to Webhook" ... client: connection to private network is blocked: host "miniflux-ai" resolves to a non-public IP address" </summary>
  
Starting with Miniflux 2.2.18, `INTEGRATION_ALLOW_PRIVATE_NETWORKS=1` must now be enabled to access third-party integration services hosted on a local network. See the [official release notes](https://github.com/miniflux/v2/releases/tag/2.2.18) for details.

</details>

## Contributing

Feel free to fork this repository and submit pull requests. Contributions and issues are welcome!

<a href="https://github.com/Qetesh/miniflux-ai/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Qetesh/miniflux-ai" />
</a>

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Qetesh/miniflux-ai&type=Date)](https://star-history.com/#Qetesh/miniflux-ai&Date)

## License

This project is licensed under the MIT License.
