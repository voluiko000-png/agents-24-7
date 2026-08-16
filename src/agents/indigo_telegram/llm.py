# -*- coding: utf-8 -*-
"""Один вызов LLM через стопку бесплатных провайдеров.

Все провайдеры OpenAI-совместимые -> один код на всех.
Кончился лимит (429) или провайдер лёг -> берём следующего, а упавшего
кладём в cooldown-файл, чтобы следующий запуск скрипта его не дёргал.

Ключи: .llm_keys.json рядом с файлом или переменные окружения
(GROQ_API_KEY, CEREBRAS_API_KEY, MISTRAL_API_KEY, OPENROUTER_API_KEY,
GEMINI_API_KEY, COHERE_API_KEY, CLOUDFLARE_API_KEY). Без ключей работает
только pollinations.

    from llm import ask
    text = ask("Напиши отклик на заказ", system="Ты фрилансер")
"""
import json
import os
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(HERE, ".llm_keys.json")
COOLDOWN_FILE = os.path.join(HERE, ".llm_cooldown.json")
LAST_PROVIDER_FILE = os.path.join(HERE, ".llm_last_provider.json")
COOLDOWN_SEC = 15 * 60

# ponytail: 02.08.2026 — проверено, Moonshot/Kimi (platform.moonshot.ai) НЕ добавлен.
# Веб-чат kimi.com бесплатен, но это не API. Сам developer API требует пополнение
# минимум $1 для активации ключа — постоянного бесплатного тира у API нет. Раз это
# платно, в список бесплатных провайдеров ниже он не идёт.
#
# ponytail: 02.08.2026 — аудит ЗАКЛАДКИ_И_ИНСТРУМЕНТЫ.md, тоже НЕ добавлены:
# - xAI/Grok (console.x.ai) — ключ не заработает без привязанной карты
#   (Billing → добавить карту), бессрочного бесплатного тира нет, кредиты
#   сгорают за 30 дней.
# - Perplexity (Sonar API) — только пробные $25-50 кредитов на старте,
#   дальше чистый pay-as-you-go, бесплатного тира для API нет (бесплатны
#   только 5 Pro-поисков/день в самом чате, не API).
# - Hugging Face Inference Providers (router.huggingface.co, ключ "hf" уже
#   есть в .llm_keys.json) — формально OpenAI-совместим, но бесплатный лимит
#   $0.10/месяц — на практике пара запросов, не стоит усложнения.
# - Gemini/AI Studio, NotebookLM, Stitch, Reve, Gamma, Canva, HeyGen, Framer —
#   либо это тот же Gemini API (уже подключён), либо нет текстового
#   OpenAI-совместимого чат-API вообще (это инструменты для картинок/дизайна/
#   презентаций/видео-аватаров, не для llm.py).

# (имя, base_url, поле ключа, модель) — порядок = приоритет
PROVIDERS = [
    # ponytail: 14.08.2026 — проверено вживую (HTTP 200), Groq раздаёт openai/gpt-oss-120b
    # (настоящая открытая модель OpenAI, 120B) бесплатно и быстро. Поставлена первой —
    # самая мощная модель во всей стопке. llama-3.3-70b-versatile оставлена вторым
    # запасным вариантом на том же ключе (другой лимит запросов, не тратит квоту 120b).
    ("groq",         "https://api.groq.com/openai/v1",                        "groq",       "openai/gpt-oss-120b"),
    ("groq_llama70b","https://api.groq.com/openai/v1",                        "groq",       "llama-3.3-70b-versatile"),
    # ponytail: 07.08.2026 — cerebras отключён: модель "llama-3.3-70b" отдаёт 404
    # model_not_found, cerebras сменили список моделей с 02.08. 14.08.2026 перепроверено:
    # каталог теперь отдаёт gpt-oss-120b/zai-glm-4.7, но аккаунт на 402 Payment required
    # (квота исчерпана) — не конфиг, биллинг. Возвращать, когда/если квота обновится.
    ("gemini",       "https://generativelanguage.googleapis.com/v1beta/openai", "gemini",   "gemini-2.5-flash"),
    ("openrouter",   "https://openrouter.ai/api/v1",                          "openrouter", "openai/gpt-oss-20b:free"),
    # ponytail: 07.08.2026 — openrouter_deepseek/openrouter_qwen отключены: OpenRouter
    # убрал именно эти ":free"-слаги ("unavailable for free, use deepseek/deepseek-chat-v3.1
    # instead" — платный). Проверено вживую 07.08, не догадка. 14.08.2026: gpt-oss-120b:free
    # тоже сняли с бесплатного тира тем же способом ("use openai/gpt-oss-120b instead" —
    # платный слаг) — не добавлять, 20b:free остаётся единственным бесплатным здесь.
    ("mistral",      "https://api.mistral.ai/v1",                             "mistral",    "mistral-small-latest"),
    ("cohere",       "https://api.cohere.ai/compatibility/v1",                "cohere",     "command-r-plus-08-2024"),
    # ponytail: 14.08.2026 — GitHub Models НЕ временно лежит, он полностью и необратимо
    # закрыт (github.blog/changelog, "GitHub Models is now retired", отключение 30.07.2026,
    # без исключений — плейграунд/каталог/inference API/BYOK убраны целиком). Убран из
    # списка, не оставлять "на подхвате" — 410 никогда не сменится на 200.
    # ponytail: account id зашит в base_url — это не секрет, привязан к одному аккаунту Cloudflare
    ("cloudflare",   "https://api.cloudflare.com/client/v4/accounts/712103fd9046a3d9f5db3aba677aa20b/ai/v1", "cloudflare", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
    # ponytail: 02.08.2026 — найдены веб-поиском, оба реально free tier без карты,
    # OpenAI-совместимые. Ключей пока нет ни в .env, ни в .llm_keys.json — просто
    # молча пропускаются в available(), пока Валера не добавит NVIDIA_API_KEY /
    # SAMBANOVA_API_KEY.
    ("nvidia",       "https://integrate.api.nvidia.com/v1",                   "nvidia",     "meta/llama-3.3-70b-instruct"),
    ("sambanova",    "https://api.sambanova.ai/v1",                           "sambanova",  "Meta-Llama-3.3-70B-Instruct"),
    # ponytail: 02.08.2026 — аудит закладок. Поле "together" уже есть в
    # .llm_keys.json, но пустое (плейсхолдер) — молча пропускается, пока
    # Валера не впишет реальный ключ с together.ai. Модель с суффиксом
    # "-Free" у Together AI бессрочно бесплатна и не тратит $5 триала —
    # обычные модели этого провайдера платные, кроме этой модели ничего не добавлять.
    ("together",     "https://api.together.xyz/v1",                          "together",   "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"),
    ("pollinations", "https://text.pollinations.ai/openai",                   None,         "openai-fast"),
]


def _read_json(path, default):
    try:
        # ponytail: utf-8-sig — PowerShell (Out-File) пишет ключи с BOM, plain utf-8 роняет json.loads
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return default


def _key(field):
    if field is None:
        return ""
    keys = _read_json(KEYS_FILE, {})
    return (keys.get(field) or os.environ.get(field.upper() + "_API_KEY") or "").strip()


def _cooling(name, cooldowns):
    return cooldowns.get(name, 0) > time.time()


def available():
    """Провайдеры, готовые принять запрос прямо сейчас."""
    cooldowns = _read_json(COOLDOWN_FILE, {})
    return [p[0] for p in PROVIDERS
            if (p[2] is None or _key(p[2])) and not _cooling(p[0], cooldowns)]


def ask(prompt, system=None, max_tokens=1200, temperature=0.7, timeout=60):
    """Ответ первого живого провайдера или None, если легли все."""
    messages = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
    cooldowns = _read_json(COOLDOWN_FILE, {})

    for name, base, field, model in PROVIDERS:
        key = _key(field)
        if field is not None and not key:
            continue
        if _cooling(name, cooldowns):
            continue
        payload = {"model": model, "messages": messages}
        if key:
            # ponytail: анонимный тариф pollinations отбивает любые лишние параметры
            payload.update(max_tokens=max_tokens, temperature=temperature)
        # ponytail: 14.08.2026 — gpt-oss модели (reasoning-модели) тратят часть
        # max_tokens на скрытые рассуждения раньше финального ответа; при
        # маленьком max_tokens (короткие JSON-решения browser_agent.py) это
        # съедает весь бюджет и возвращает пустой content. reasoning_effort=low
        # проверен вживую (Groq): оставляет содержательный ответ даже при
        # max_tokens=30. Не трогает другие модели — поле игнорируется, если
        # провайдер его не понимает, максимум лишний параметр в payload.
        if "gpt-oss" in model:
            payload["reasoning_effort"] = "low"
        try:
            r = requests.post(
                base + "/chat/completions",
                headers={"Authorization": "Bearer " + key} if key else {},
                json=payload,
                timeout=timeout,
            )
            if r.status_code == 200:
                # ponytail: лог того, какой именно провайдер ответил — раньше нигде
                # не записывалось, а Валере/проверке важно знать, кто сгенерировал ответ.
                try:
                    with open(LAST_PROVIDER_FILE, "w", encoding="utf-8") as f:
                        json.dump({"provider": name, "model": model, "at": time.strftime("%Y-%m-%d %H:%M:%S")}, f)
                except OSError:
                    pass
                # ponytail: 09.08.2026 - r.json() иногда угадывало кодировку неверно
                # для кириллических ответов (requests чарсет-хевристика на JSON без
                # заголовка charset) - результат сохранялся в очередь уже необратимо
                # битым (реальные replacement-символы, не просто дисплей-баг). Декодируем
                # байты как UTF-8 явно, без угадывания.
                data = json.loads(r.content.decode("utf-8"))
                content = data["choices"][0]["message"]["content"].strip()
                # ponytail: 14.08.2026 — HTTP 200 с пустым content реален (reasoning-модели
                # без остатка бюджета на финальный ответ) — раньше это молча возвращалось
                # как "успех", хотя вызывающий код получал пустую строку. Пустой ответ —
                # это отказ, идём к следующему провайдеру, а не отдаём "" наверх.
                if content:
                    return content
            # 429 = лимит, 5xx = провайдер лёг: обоих в отстойник и идём дальше
            if r.status_code == 429 or r.status_code >= 500:
                cooldowns[name] = time.time() + COOLDOWN_SEC
            # ponytail: 4xx (кривой ключ/модель) не кэшируем — чинится правкой конфига
        except Exception:
            cooldowns[name] = time.time() + COOLDOWN_SEC

    with open(COOLDOWN_FILE, "w", encoding="utf-8") as f:
        json.dump(cooldowns, f)
    return None


if __name__ == "__main__":
    assert available(), "нет ни одного провайдера — проверь .llm_keys.json"
    print("готовы:", ", ".join(available()))
    out = ask("Ответь ровно одним словом: тест", max_tokens=20)
    assert out, "все провайдеры отказали"
    print("ответ:", out)
