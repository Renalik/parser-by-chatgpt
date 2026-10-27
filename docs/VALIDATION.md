# Выполненные проверки

26 октября 2026, Python 3.12.14, Node.js 24.19.0.

- Повторная установка `pip install -r backend/requirements.lock`: успешно, `pip check` без конфликтов.
- `npm ci` и `npm run build`: успешно, TypeScript и production-сборка Vite.
- `python -m pytest -q`: **27 passed, 1 skipped**. Пропущен только живой тест, требующий `DGIS_INTEGRATION_KEY`. Есть предупреждение об устаревающем имени BlockingPortal в зависимости Starlette, на результат не влияет.
- Playwright с системным Chromium: **1 passed**. Подключение демо, выбор города/категории, фильтр телефона, поиск, таблица и карточка, скачивание XLSX, планшетная ширина 768 px без горизонтального переполнения и ошибок JavaScript.
- Итоговый `python scripts/run.py`: GET `/`, `/api/health`, `/api/meta` вернули 200.
- `docker compose config --quiet`: успешно.
- Docker-образ: собран с системным доверенным CA облачного прокси через временный BuildKit mount. Контейнер запущен непривилегированным пользователем; HTTP/API, демопоиск, XLSX с 10 строками и 2 выбранными колонками проверены. Полная команда Compose с volume отдельно не проверялась.
- `git diff --check`: успешно.

Не проверены реальные поиски 2ГИС, разрешения и тариф ключа, PostgreSQL и серверное развёртывание с внешним HTTPS proxy. Отсутствующий ключ не заменяется тестовыми данными; демо включается отдельно.

## Windows EXE — 27 октября 2026

- [GitHub Actions: Windows EXE, сборка 1](https://github.com/Renalik/parser-by-chatgpt/actions/runs/40544179343): успешно на Windows runner. Серверные тесты, frontend, упаковка, smoke test готового EXE и публикация релиза завершились успешно.
- [Готовый EXE](https://github.com/Renalik/parser-by-chatgpt/releases/download/windows-build-1/2GIS-Business-Parser.exe) скачан повторно: HTTP 200, 24 481 325 байт, PE-заголовок MZ. SHA256 совпал с опубликованной контрольной суммой: `b6808bc0ea101981542a72197d600a5b0bacda61617057b3aaa988dee612e78c`.
- Упакованный EXE проверен на Windows: HTTP/UI, демопоиск на 10 записей, XLSX на 10 записей и 2 колонки, защищённое хранение ключа Windows DPAPI. Реальный API в этом тесте не использовался.
- Размер извлекаемых библиотек и ресурсов по оглавлению архива PyInstaller: 36 938 917 байт. EXE и распаковка вместе — около 61,4 МБ, без пользовательских данных.
- Локально Linux: `29 passed, 2 skipped` (живой API и Windows DPAPI); launcher smoke test и дополнительно однофайловая Linux-упаковка успешно выполнили демопоиск и экспорт.
