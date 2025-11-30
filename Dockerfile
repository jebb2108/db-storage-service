FROM python:3.13.3

WORKDIR /app

ENV PYTHONPATH=/app

ENV BASE_URL=postgres
ENV DEBUG=TRUE
ENV LOG_LEVEL=INFO
ENV DB_API_PORT=4040

COPY pyproject.toml poetry.lock ./

# Установка Poetry
RUN pip install poetry

# Установка зависимостей
RUN poetry install --no-root

COPY src/ ./src/

CMD ["poetry", "run", "python", "src/main.py"]