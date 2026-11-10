# 5 листов — рейтинг чаёв по магазинам

Один и тот же чай продают разные магазины — по отзывам видно, где он лучше, почём и какие ноты в нём слышат.
FastAPI + PostgreSQL на бэкенде, React + Vite на фронте.

## Разработка

```bash
cp .env.example .env                                   # и заполнить
docker compose -f deploy/docker-compose.yml up -d      # Postgres, бэкенд с --reload, сборка фронта с --watch
poetry install                                          # зависимости на хосте — для тестов, миграций, линтера
alembic upgrade head                                    # схема БД
docker compose -f deploy/docker-compose.yml exec backend python -m back.seed --author <ваша почта>   # демо-данные
```

Сайт — http://localhost:8000, API — http://localhost:8000/docs.
Фронт собирает контейнер `frontend` (на хосте нужен Node 20+).

## Тесты

```bash
poetry run pytest                                               # бэкенд: отдельная база tea_rates_test, схема — миграциями
docker compose -f deploy/docker-compose.yml exec frontend npm test   # фронт: vitest
poetry run ruff check back && poetry run ruff format --check back
```

## Миграции

Схемой управляет Alembic (`back/migrations`). Поменяли модели — создайте миграцию:

```bash
alembic revision --autogenerate -m "что поменялось"
alembic upgrade head
```

Тест `test_migrations_match_models` упадёт, если модели и миграции разошлись.

## Деплой

См. [deploy/README.md](deploy/README.md): VPS, HTTPS через Caddy, почта, бэкапы.
