# The stylesheet is built with the Tailwind CLI in a Node stage, then only
# the CSS file is copied into the Python image.
FROM node:22-alpine AS css
WORKDIR /build
COPY package.json package-lock.json tailwind.config.js ./
RUN npm ci --no-audit --no-fund
COPY school_portal/templates school_portal/templates
COPY school_portal/static school_portal/static
RUN npm run css

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml ./
COPY school_portal school_portal
RUN pip install .
COPY alembic.ini ./
COPY migrations migrations
COPY docker/entrypoint.sh /entrypoint.sh
COPY --from=css /build/school_portal/static/dist /app/school_portal/static/dist
# The package was installed before the CSS existed; serve static files from /app.
ENV PYTHONPATH=/app UPLOAD_DIR=/data/uploads
RUN mkdir -p /data/uploads
EXPOSE 8000
ENTRYPOINT ["sh", "/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "school_portal:create_app()"]
