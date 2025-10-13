# builder stage; uses own file system
FROM python:3.12-slim AS builder
# mkdir -p /fastapi_ddd_template && cd /fastapi_ddd_template (-p creates /fastapi_ddd_template if not exists)
WORKDIR /fastapi_ddd_template
# copy pyproject.toml poetry.lock from host to builder ./
COPY pyproject.toml poetry.lock ./
RUN pip install --upgrade pip
# make sure poetry version mathes poetry.lock version
RUN pip install --no-cache-dir poetry==2.2.1
# don't create virtual env
RUN poetry config virtualenvs.create false
# install dependecies from poetry.lock without dev and self package 
RUN poetry install --without=dev --no-root

# final stage: image build
FROM python:3.12-slim
WORKDIR /fastapi_ddd_template
# copy packages from builder to image
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# copy from host to image
COPY ./app ./app
COPY ./entrypoint.py ./entrypoint.py
COPY ./alembic.ini ./alembic.ini

# rm -rf /var/lib/apt/lists/* cleans apt cache to reduce image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*
