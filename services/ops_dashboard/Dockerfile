FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock* ./
COPY shared/ shared/
COPY services/ops_dashboard/ services/ops_dashboard/
RUN uv sync --frozen --package gutp-ops-dashboard
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "uvicorn", "gutp_ops_dashboard.main:app", "--host", "0.0.0.0", "--port", "8000"]
