FROM python:3.13.3
LABEL authors="Gabriel Bouchard"

WORKDIR /app

ENV PYTHONPATH=/app

COPY pyproject.toml poetry.lock ./

# Установка Poetry
RUN pip install poetry

# Установка зависимостей
RUN poetry install --no-root

COPY src/ ./src/

CMD ["poetry", "run", "python", "src/main.py"]