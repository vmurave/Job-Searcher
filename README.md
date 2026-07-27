# Leadership Jobs Digest

Ежедневный AI-бот, который в 09:00 собирает новые вакансии руководящего звена
(Lead / Head / Teamlead / Руководитель) с заранее заданного списка карьерных
сайтов и показывает результат на локальной веб-странице.

## Архитектура

- **FastAPI** + **APScheduler** — один долгоживущий процесс. APScheduler
  внутри FastAPI триггерит скрапинг ежедневно в 09:00.
- **SQLite** (`jobs.db`) — хранилище для дедупликации.
- Адаптеры по платформам в [platforms/](platforms/):
  - [greenhouse_api.py](platforms/greenhouse_api.py) — Greenhouse board API
    (Nebius, Toloka, N26, Miro, Palta, Flo, Xsolla, Mercuryo, Semrush).
  - [hh_api.py](platforms/hh_api.py) — публичный HH.ru API
    (employer/44764, employer/1829949).
  - [playwright_generic.py](platforms/playwright_generic.py) — fallback на
    headless Chromium для JS-SPA (Revolut, Avito, T-Bank, JetBrains и др.).

## Запуск (Windows)

```cmd
setup.bat        :: один раз: создаёт .venv, ставит deps, качает Chromium
run.bat          :: запускает сервер на http://localhost:8000
```

Оставьте окно `run.bat` открытым — оно держит процесс с APScheduler.

## Endpoints

| Метод | Путь        | Описание                                              |
|-------|-------------|-------------------------------------------------------|
| GET   | `/`         | Все найденные вакансии, сгруппированы по платформам   |
| GET   | `/today`    | Только вакансии, найденные сегодня                    |
| POST  | `/refresh`  | Запустить скрапинг прямо сейчас (JSON-ответ)          |
| GET   | `/healthz`  | Статус + время последнего запуска                     |

## Ручной разовый запуск

```cmd
.venv\Scripts\activate
python scheduler.py
```

Печатает per-platform отчёт: сколько вакансий получено, сколько прошло
фильтр по ключевым словам, сколько новых записалось в БД.

## Автозапуск на Windows

`run.bat` нужно держать запущенным круглосуточно. Самый простой способ —
зарегистрировать его в Task Scheduler с триггером **At log on** и опцией
**Run only when user is logged on**.

```powershell
schtasks /Create /SC ONLOGON /TN "LeadershipJobsDigest" /TR "%CD%\run.bat" /RL HIGHEST
```

## Расширение списка платформ

Добавьте запись в `PLATFORMS` в [platforms/__init__.py](platforms/__init__.py).
Для платформы с Greenhouse достаточно правильного slug. Для произвольного
сайта — `PlaywrightAdapter(name=..., public_url=...)`.

## Известные ограничения

- **Generic Playwright-адаптер** ищет ссылки, путь которых содержит
  `/job`, `/career`, `/vacancy` и т.п. Сайты с нестандартной разметкой
  могут давать 0 результатов — для них стоит написать свой адаптер.
- Slugs Greenhouse — best-guess; если у компании другой ATS, адаптер
  получит 404 и платформа будет помечена ошибкой в `run_log`. В этом
  случае замените на `PlaywrightAdapter`.
- Сайты под Cloudflare могут блокировать headless Chromium. Решение —
  использовать `playwright-stealth` или искать публичный API сайта.
