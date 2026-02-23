# builder stage; uses own file system
FROM python:3.12-slim AS builder
# mkdir -p /dddapitpl && cd /dddapitpl (-p creates /dddapitpl if not exists)
WORKDIR /dddapitpl
# copy pyproject.toml poetry.lock from host to builder ./
COPY pyproject.toml poetry.lock ./
RUN pip install --upgrade pip
# make sure poetry version mathes poetry.lock version
RUN pip install --no-cache-dir poetry==2.2.1
# don't create virtual env
RUN poetry config virtualenvs.create false

# install dependecies from poetry.lock without self package
ARG WITH_DEV=false
# INTERFACE selects which dependency group to install (fastapi or django)
ARG INTERFACE=fastapi
RUN if [ "$INTERFACE" = "django" ]; then \
      EXCLUDE="--without=fastapi"; \
    else \
      EXCLUDE="--without=django"; \
    fi; \
    if [ "$WITH_DEV" = "true" ]; then \
      poetry install $EXCLUDE --no-root ; \
    else \
      poetry install --without=dev $EXCLUDE --no-root ; \
    fi

# final stage: image build
FROM python:3.12-slim
WORKDIR /dddapitpl
# copy packages from builder to image
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# copy from host to image
COPY ./app ./app
COPY ./entrypoint.py ./entrypoint.py
COPY ./alembic.ini ./alembic.ini
