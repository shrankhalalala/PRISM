FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 ca-certificates && rm -rf /var/lib/apt/lists/* \
    && groupadd -g 10001 prism && useradd -u 10001 -g prism -m prism
COPY pyproject.toml requirements-phase3-tested.txt ./
RUN mkdir -p prism && touch prism/__init__.py
RUN --mount=type=cache,target=/root/.cache/pip pip install -c requirements-phase3-tested.txt -e '.[phase3,neo4j]'
COPY --chown=prism:prism prism ./prism
COPY --chown=prism:prism scripts ./scripts
COPY --chown=prism:prism models ./models
COPY --chown=prism:prism data ./data
COPY --chown=prism:prism docs ./docs
COPY --chown=prism:prism reports ./reports
RUN mkdir -p /app/artifacts && chown -R prism:prism /app/artifacts
USER prism
EXPOSE 5050
CMD ["gunicorn", "--bind", "0.0.0.0:5050", "--workers", "2", "--threads", "2", "--timeout", "30", "prism:create_app()"]
