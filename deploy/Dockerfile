FROM python:3.12-slim

RUN pip install --upgrade pip && pip install poetry

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root

COPY back ./back

#Запускать из директории TeaRates командой: docker build -f deploy/Dockerfile -t tea_rates .