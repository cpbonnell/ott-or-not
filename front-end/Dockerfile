FROM python:3.12

RUN pip install --upgrade pip && pip install poetry
ENV POETRY_VIRTUALENVS_CREATE=false


WORKDIR /app
COPY pyproject.toml *.lock ./
RUN poetry install --no-root --no-ansi --no-interaction

COPY . .
RUN poetry install --no-ansi --no-interaction

EXPOSE 8080

CMD ["flet", "run", "--web", "--port", "8080"]