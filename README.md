# AI Coding Models Leaderboard

Интерактивная TUI-таблица AI-моделей для кодинга. ~290 моделей из 6 источников с сортировкой, фильтрацией и копированием конфига для opencode.

## Установка

```bash
pip install -r requirements.txt
```

## Запуск

```bash
python app.py
```

При первом запуске таблица пустая — нажмите `r` для загрузки данных.

## Управление

| Клавиша | Действие |
|---|---|
| `r` | Обновить данные (все источники параллельно) |
| `↑` / `↓` | Навигация по строкам |
| Клик по заголовку | Сортировка по столбцу (повторный клик — обратный порядок) |
| `f` | Показать только бесплатные модели |
| `Enter` | Скопировать конфиг-сниппет в буфер обмена (с trailing comma) |
| `Shift+Enter` | То же, но без trailing comma (для последней записи) |
| `q` / `Ctrl+C` | Выйти |

## Столбцы

| Столбец | Источники | Пример |
|---|---|---|
| Model | Все источники | Claude Opus 4.7 |
| Provider | ArtificialAnalysis, статические данные | Anthropic |
| Params (B) | ArtificialAnalysis, HuggingFace | 70B |
| Context (K) | ArtificialAnalysis, OpenRouter, LiteLLM, статические данные | 200K |
| Output (K) | OpenRouter, LiteLLM | 8K |
| Coding | SWE-bench, Aider, ArtificialAnalysis (норм.) | 88.0% |
| Free via | OpenRouter (live), FCM статик (14 провайдеров) | OpenRouter, NIM, Groq +5 |

### Колонка Coding

Показывает лучшую доступную coding-метрику в единой шкале 0–100%:

1. **SWE-bench %** — доля задач по починке реального кода, решённых bash-only агентом (bash-only leaderboard, яблоки к яблокам)
2. **Aider %** — pass rate на 225 задачах Exercism в 6 языках (polyglot benchmark)
3. **AA Coding (норм.)** — Coding Index от ArtificialAnalysis, нормализованный к 0–100% делением на эмпирический максимум шкалы (60)

Если для модели доступно несколько источников, показывается SWE-bench → Aider → AA в порядке приоритета. Значения из разных источников не суммируются и не смешиваются в одной строке.

## Копирование сниппета для opencode

`Enter` копирует JSON-блок с правильным отступом (8/10/12 пробелов) и trailing comma, готовый к вставке в `~/.config/opencode/opencode.json`:

```json
        "mistralai/devstral-small-2505:free": {
          "name": "Devstral Small",
          "limit": {
            "context": 131000,
            "output": 8192
          }
        },
```

**Куда вставлять:** в секцию `provider.<api_provider>.models` — нужный блок показывается в статус-баре сразу после копирования, например:

> Copied **Devstral Small** → **provider.openrouter.models**

`api_provider` резолвится по приоритету:

1. `free_providers[0]` — первый элемент списка бесплатных провайдеров (отсортирован по `PROVIDER_PRIORITY`, так что это «лучший» вариант).
2. Fallback `openrouter` если задан `openrouter_id`.
3. `None` — копируется как есть, в статус-баре появляется предупреждение ⚠.

**Имя модели** для ключа `"..."` берётся в таком порядке:

1. `model_ids[api_provider]` — provider-specific API ID из пакета `free-coding-models` (например, для Groq это `llama-3.3-70b-versatile`, а не `Llama 3.3 70B:free`). Доступно после `r` (refresh).
2. `openrouter_id` — fallback для openrouter (OpenRouter-стиль ID с `:free`).
3. `<name>:free` — placeholder, помечается ⚠ в статус-баре; пользователь должен подставить правильный ID вручную.

`Shift+Enter` — то же самое, но **без trailing comma** (для вставки последней записью, где запятая не нужна).

Значения `context` и `output` берутся напрямую из OpenRouter API. Маппинг провайдеров — в `core/opencode_providers.py`.

## Источники данных

| Источник | Что даёт | Метод |
|---|---|---|
| [ArtificialAnalysis](https://artificialanalysis.ai/leaderboards/models) | Название, провайдер, параметры, контекст, Coding Index | HTML (RSC payload) |
| [OpenRouter](https://openrouter.ai/api/v1/models) | Бесплатные модели (:free), контекст, лимит вывода | REST API |
| [free-coding-models](https://github.com/nicholasgasior/free-coding-models) | Ещё 13 провайдеров бесплатного доступа: NIM, Groq, Cerebras, GitHub, Google AI, Mistral, Cloudflare, SambaNova, OVHcloud, Scaleway, DashScope, ZAI, Codestral | Статик (sources.js) |
| [SWE-bench](https://www.swebench.com) | SWE-bench % (bash-only leaderboard, 48 моделей) | Static HTML + JSON |
| [Aider](https://aider.chat/docs/leaderboards/) | Coding pass rate %, 225 задач (69 моделей) | Static HTML |
| [HuggingFace](https://huggingface.co/api/models) | Параметры open-weight моделей (safetensors metadata) | REST API |
| [LiteLLM](https://github.com/BerriAI/litellm) | `output_tokens`, function-calling/vision-флаги, fallback для `context_k` (~982 chat/responses модели) | Статический JSON |

После слияния к данным применяется статическое обогащение (`core/static_data.py`) — заполняет провайдера, контекст и приблизительные coding-скоры для моделей, которых нет в scrapers (около 50 записей). Дополнительно заполняет колонку **Free via** данными из `core/free_providers_data.py` — нормализованный маппинг 109 моделей на 14 провайдеров бесплатного доступа, извлечённый из локального пакета `free-coding-models`. **LiteLLM**-источник (`core/litellm_data.py`) параллельно загружается при `r` и заполняет `output_tokens` (было пусто у 95% моделей → теперь у ~57%), а также флаги `supports_function_calling` / `supports_vision` (невидимые в таблице, доступны через API). Стратегия матчинга: прямое совпадение нормализованного имени + двусторонний substring с порогом длины 70% (отсекает ложные матчи вроде «Qwen3.5 0.8B» → «Qwen3 8B»).

### Слияние источников

Модели из разных источников объединяются по нечёткому совпадению имён (rapidfuzz, порог 95). Поля заполняются из первого источника, который их знает. При обновлении статическое обогащение применяется последним — никогда не перезаписывает свежие скрейпнутые данные.

Кэш (`cache.json`) не перезаписывается, если при обновлении все источники вернули пустой результат.

## Бесплатные API провайдеры

Сравнительная таблица платформ с бесплатным доступом к языковым моделям, от наиболее щедрых к наименее. Все ссылки ведут на страницу регистрации или API-документацию.

| Провайдер | Бесплатные модели | Лимиты | Регистрация |
|---|---|---|---|
| [OpenRouter](https://openrouter.ai) | 100+ моделей с `:free` суффиксом | Rate limit по модели, без ключа невозможно | [API keys](https://openrouter.ai/keys) |
| [Google AI Studio](https://aistudio.google.com) | Gemini 2.5 Pro/Flash, Flash Lite и др. | 250–1500 RPD (зависит от модели) | [Get API key](https://aistudio.google.com/apikey) |
| [GitHub Models](https://github.com/marketplace/models) | GPT-4.1/Mini/Nano, Llama 4, Mistral и др. | Low/High tier: 15–50 RPM, 150–450K TPD | [GitHub account](https://github.com/marketplace/models) |
| [NVIDIA NIM](https://build.nvidia.com) | 50+ моделей (Llama, Qwen, Mistral, DeepSeek…) | 1000 API calls/month бесплатно | [NVIDIA account](https://build.nvidia.com) |
| [Groq](https://console.groq.com) | Llama 4, Qwen3, DeepSeek и др. | 6K–30K TPM, 500–14.4K RPD | [Console](https://console.groq.com) |
| [Cerebras](https://cloud.cerebras.ai) | Llama, Qwen3 235B, GLM | 60 RPM, 1M TPD | [Sign up](https://cloud.cerebras.ai) |
| [SambaNova](https://cloud.sambanova.ai) | Llama 4, MiniMax M2.5, DeepSeek | 50–600 RPM | [Sign up](https://cloud.sambanova.ai) |
| [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/) | Llama 4, Qwen3, Gemma 4, GLM | 10K neurons/day бесплатно | [Cloudflare account](https://dash.cloudflare.com) |
| [Mistral La Plateforme](https://console.mistral.ai) | Mistral Large/Medium/Small, Devstral, Magistral | Free experiment plan, лимиты не раскрываются | [Console](https://console.mistral.ai) |
| [Codestral](https://codestral.mistral.ai) | Codestral (специализированная coding модель) | Бесплатно для некоммерческого использования | [Sign up](https://codestral.mistral.ai) |
| [Pollinations.ai](https://pollinations.ai) | Kimi K2, GLM-4.7, Gemini Flash, DeepSeek V3, GPT OSS 20B и др. | Без ключа, без регистрации, rate limit неизвестен | [API docs](https://pollinations.ai/p/text) |
| [LLM7.io](https://llm7.io) | Codestral, Llama 4 Scout, Mistral Large/Medium/Small, Qwen2.5 Coder, GPT-4.1 Nano | Без ключа, без регистрации | [API docs](https://llm7.io) |
| [Scaleway](https://www.scaleway.com/en/generative-apis/) | Qwen3, Mistral, Gemma 3, DeepSeek и др. | Free tier: лимиты по модели | [Sign up](https://console.scaleway.com) |
| [OVHcloud AI Endpoints](https://endpoints.ai.cloud.ovh.net) | Llama 3.3, Qwen3, Mistral, Codestral и др. | Free tier: лимиты по токенам | [Sign up](https://www.ovhcloud.com) |
| [DashScope (Alibaba)](https://dashscope.aliyuncs.com) | Qwen3 Max/Plus, Qwen3 Coder и др. | Free tier: первые N токенов бесплатно | [Console](https://dashscope.console.aliyun.com) |
| [ZAI.chat](https://zai.chat) | GLM-4.5-Flash, GLM-4.7-Flash | Без ключа или по API-ключу | [API docs](https://zai.chat) |
| [Hugging Face Inference API](https://huggingface.co/inference-api) | Тысячи open-weight моделей | Free tier: serverless, rate limited | [Sign up](https://huggingface.co/join) |
| [Together AI](https://www.together.ai) | Llama, Qwen, Mixtral и др. | $5 кредитов при регистрации | [Sign up](https://api.together.ai) |
| [Fireworks AI](https://fireworks.ai) | Llama, Qwen, Mixtral и др. | $1 кредит при регистрации | [Sign up](https://fireworks.ai) |
| [Perplexity API](https://docs.perplexity.ai) | Sonar, r1-1776 | $5 кредитов при регистрации | [Sign up](https://www.perplexity.ai/settings/api) |
| [Cohere](https://cohere.com) | Command, Embed | Free trial: 1K RPM (non-commercial) | [Sign up](https://dashboard.cohere.com) |
| [Deepinfra](https://deepinfra.com) | Llama, Qwen, Mistral и др. | $1.8 кредита при регистрации | [Sign up](https://deepinfra.com) |
| [Replicate](https://replicate.com) | Llama, Stable Diffusion и др. | $0.005 кредита при регистрации | [Sign up](https://replicate.com) |
| [Inference.net](https://inference.net) | Llama, Mixtral и др. | $5 кредитов при регистрации | [Sign up](https://inference.net) |
| [Featherless.ai](https://featherless.ai) | Большой список open-weight моделей | Free tier с лимитами | [Sign up](https://featherless.ai) |
| [Novita AI](https://novita.ai) | Llama, Qwen, DeepSeek и др. | $0.5 кредита при регистрации | [Sign up](https://novita.ai) |
| [Chutes AI](https://chutes.ai) | Llama, Qwen, DeepSeek и др. | Без ключа (rate limited) | [API docs](https://chutes.ai) |

> Провайдеры без регистрации (Pollinations.ai, LLM7.io, Chutes AI) не требуют API-ключа — достаточно HTTP-запроса. Остальные требуют регистрацию, но предоставляют бесплатный tier.

## Добавление нового источника

1. Создать `scrapers/mysource.py`:

```python
from scrapers.base import BaseScraper
from core.models import ModelRecord

class MySourceScraper(BaseScraper):
    name = "mysource"

    async def _fetch(self) -> list[ModelRecord]:
        resp = await self._get("https://example.com/api")
        return [ModelRecord(name="...", provider="...")]
```

2. Добавить в `scrapers/__init__.py`:

```python
from scrapers.mysource import MySourceScraper
SCRAPER_REGISTRY = [..., MySourceScraper()]
```

`BaseScraper` автоматически оборачивает исключения: упавший источник не блокирует остальные и показывается как предупреждение в статусной строке.

## Структура проекта

```
models_data_table/
├── app.py                        # точка входа (Textual App)
├── ui/
│   └── table_view.py             # экран: таблица, биндинги, рендер
├── scrapers/
│   ├── __init__.py               # SCRAPER_REGISTRY — единственный файл для изменения при добавлении источника
│   ├── base.py                   # BaseScraper: fetch(), _get(), обработка ошибок
│   ├── artificialanalysis.py     # RSC payload парсинг
│   ├── openrouter.py             # REST API, text→text фильтр
│   ├── swebench.py               # bash-only leaderboard из <script id="leaderboard-data">
│   ├── aider.py                  # polyglot leaderboard, дедупликация по лучшему скору
│   └── huggingface.py            # safetensors.total для open-weight моделей
├── core/
│   ├── models.py                 # ModelRecord dataclass
│   ├── merger.py                 # нечёткое слияние, порог 95
│   ├── cache.py                  # read/write cache.json
│   └── static_data.py            # статическое обогащение: провайдер, контекст, скоры
├── tests/
│   └── scrapers/                 # 35 тестов, respx моки
└── cache.json                    # локальный кэш (gitignored)
```

## Тесты

```bash
pytest
```
