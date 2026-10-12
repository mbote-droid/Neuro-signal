# Runs the CLI as a non-root user, for reading untrusted recordings in isolation.
# Pin the base image by digest before release: docker pull python:3.12-slim && docker inspect.
FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv MPLCONFIGDIR=/tmp/mpl
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev && useradd --create-home --uid 10001 analyst
USER analyst
WORKDIR /data
ENTRYPOINT ["/opt/venv/bin/neurosignal"]
CMD ["--help"]
