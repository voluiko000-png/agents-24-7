# 24/7 AI Agents on GitHub Actions

Автономные агенты работают в облаке без зависимости от локального ПК.

## Структура

- Фриланс-агент: поиск заказов, отклики
- Digital-products-агент: создание товаров, публикация
- Amazon KDP агент: книги, раскраски
- Social Media агент: постинг в Telegram, YouTube, Instagram, Facebook
- `indigo_telegram` — 50 тем группы Indigo Hub (Telegram Topics): фото под
  нишу (Cloudflare Flux) + пост премиум-стиля (llm.py-каскад) 2 раза в день,
  полностью в облаке, работает даже когда ПК Валеры выключен. Секреты:
  `TELEGRAM_BOT_TOKEN`, `CLOUDFLARE_API_KEY`, `GROQ_API_KEY`,
  `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY`,
  `SAMBANOVA_API_KEY` (репозиторий публичный — токены только в GitHub
  Secrets, никогда в коде).

## Запуск

Все workflows запускаются по расписанию в GitHub Actions. Результаты синхронизируются с Obsidian.
