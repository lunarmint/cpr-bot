# For more information, refer to https://aka.ms/vscode-docker-python
FROM python:3.10.7-bullseye
LABEL maintainer="https://github.com/lunarmint/cpr-bot"

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Force UTF8 encoding for funky character handling
ENV PYTHONIOENCODING=utf-8

# Needed so imports function properly
ENV PYTHONPATH=/app

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry path to PATH
ENV PATH="${PATH}:/root/.local/bin"

# Install project dependencies with Poetry
COPY pyproject.toml .
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi --only main --all-extras

# Place where the app lives in the container
WORKDIR /app
COPY . /app

# During debugging, this entry point will be overridden.
CMD ["python", "/app/cpr/bot.py"]
