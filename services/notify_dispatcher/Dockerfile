FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock* ./
COPY shared/ shared/
COPY services/notify_dispatcher/ services/notify_dispatcher/
RUN uv sync --frozen --package gutp-notify-dispatcher
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "gutp_notify_dispatcher.main"]
