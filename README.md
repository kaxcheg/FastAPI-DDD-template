# FastAPI DDD Template

**FastAPI‑DDD Template** is a sample project that demonstrates how to
organise a FastAPI application using Domain‑Driven Design (DDD)
principles. It is built with FastAPI, SQLAlchemy and Pydantic and
provides a minimal yet complete example of how to structure a service
with clear boundaries between the domain, application, infrastructure
and interface layers. The project centres around a simple user domain
with two use cases: user creation and user authentication. The project 
includes simple Docker compose deployment solution.

## Features

-   **Domain‑Driven Architecture** -- the code base is organised into
    `domain`, `application`, `infrastructure` and `interface` layers.
    Entities, value objects and domain services live in the domain
    layer, use cases and DTOs in the application layer, database
    adapters and external services in the infrastructure layer, and HTTP
    routes and presenters in the interface layer.
-   **User entity and value objects** -- the core domain element is a
    `User` entity with immutable identifier, username, password hash,
    role and activity
    flag[\[1\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/domain/entities/user/user.py#L22-L25).
    Supporting value objects encapsulate user identifiers, raw passwords
    and
    roles[\[2\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/domain/value_objects/user_id.py#L1-L48)[\[3\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/domain/value_objects/user_role.py#L1-L6).
-   **Use cases** -- the application layer exposes explicit use cases
    for creating a user and authenticating a user. The
    `CreateUserUseCase` validates input, hashes the password, creates a
    new user via a factory method and persists it through the
    repository[\[4\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/application/use_cases/create_user.py#L54-L69).
    The `AuthenticateUserUseCase` retrieves a user by username and
    verifies the password
    hash[\[5\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/application/use_cases/authenticate_user.py#L38-L65).
-   **Ports and adapters** -- clear interfaces define repositories,
    units of work, hashing services and authentication services.
    Concrete implementations in the infrastructure layer use SQLAlchemy
    for persistence and bcrypt for hashing, while JWT is used for
    issuing access tokens.
-   **Dependency injection and FastAPI integration** -- dependencies are
    provided via FastAPI `Depends` so that the HTTP layer remains thin.
    Routes for `/users` and `/login` map incoming requests to use cases
    and
    presenters[\[6\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/routes/users.py#L19-L42)[\[7\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/routes/login.py#L22-L55).
-   **Asynchronous programming** -- the project uses SQLAlchemy's async
    API and asynchronous units of work, allowing non‑blocking database
    access.
-   **Configuration via environment variables** -- all configuration is
    loaded through a single Pydantic settings class with prefixes,
    supporting different environments (development, testing,
    production)[\[8\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/config/config.py#L21-L45).
    Example `.env` files for development and production are provided to
    help you get
    started[\[9\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/.env_example.dev#L1-L19)[\[10\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/deploy/.env_example.prod#L1-L15).
-   **Database migrations** -- Alembic is configured for schema
    migrations; an example migration creating the `users` table is
    included.
-   **Docker and Docker Compose** -- a production‑ready container image
    can be built via the provided `Dockerfile`, and
    `generate_compose.py` can produce a `docker‑compose.yml` for running
    the app together with PostgreSQL. Secrets are mounted from files to
    avoid hard‑coding
    credentials[\[11\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/deploy/docker-compose.yml#L1-L80).
-   **Admin bootstrapping script** -- a helper script `create_admin.py`
    can create an initial administrator account using environment
    variables if the bootstrap flag is
    enabled[\[12\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/scripts/create_admin.py#L32-L43).

## Architecture overview

The project follows a layered architecture inspired by DDD:

1.  **Domain layer** -- Contains pure domain objects. The `User` entity
    encapsulates identity and business rules, while value objects such
    as `UserId`, `Username`, `UserRole` and `UserRawPassword` enforce
    invariants and type safety. Domain services (e.g. `IdGenerator`)
    generate identifiers and are free of infrastructural concerns.
2.  **Application layer** -- Exposes use cases as classes that
    orchestrate domain operations. Use cases depend only on interfaces
    such as `UserRepository`, `UnitOfWork`, `PasswordHasher` and
    `AuthService`. Data transfer objects (DTOs) are defined to decouple
    the domain from external
    representations[\[13\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/application/dto/dto.py#L6-L28).
3.  **Infrastructure layer** -- Provides concrete implementations of
    ports. SQLAlchemy models map entities to tables, and async
    repositories wrap CRUD operations. Password hashing and JWT token
    services live here. Alembic configuration and migration scripts also
    belong in this layer.
4.  **Interface layer** -- Exposes a FastAPI application. Routes convert
    incoming requests into DTOs, call a use case and return responses
    via presenters. The interface layer has no knowledge of persistence
    or business logic beyond the use case interfaces.

This separation allows the domain and application layers to remain
independent from frameworks and external technologies. You can swap the
web framework or persistence mechanism without touching the core logic.

## Getting started (development)

### Prerequisites

-   Python 3.12 or higher
-   [Poetry](https://python-poetry.org/) for dependency management
-   A running PostgreSQL instance (or Docker for local Postgres)

### Setup steps

1.  **Clone the repository**

```
git clone https://github.com/kaxcheg/FastAPI-DDD-template.git
cd FastAPI-DDD-template
```

2.  **Configure environment variables**

Copy the provided development example and adjust values as needed:

```
cp .env_example.dev .env.dev
```

The `.env.dev` file defines variables such as database credentials, JWT
secret, and server
host/port[\[9\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/.env_example.dev#L1-L19).
Ensure PostgreSQL is running locally and the credentials match.

3.  **Install dependencies**

Use Poetry to install the project in a virtual environment:

```
poetry install
```

4.  **Run database migrations**

Initialize the schema using Alembic:

```
poetry run alembic upgrade head
```

5.  **Start the application**

Launch the API with Uvicorn:

```
poetry run uvicorn app.interface.http.main:app --reload --host 0.0.0.0 --port 8000
```

The interactive documentation will be available at
`http://localhost:8000/docs`.

6.  **Create an admin user (optional)**

To bootstrap an initial administrator, set `APP_BOOTSTRAP_ADMIN=true`
and provide `APP_ADMIN` and `APP_ADMIN_PASSWORD_HASH` (bcrypt hash) in
your environment. Then run:

```
poetry run python -m app.scripts.create_admin
```

The script will create an admin account if it does not already
exist[\[14\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/scripts/create_admin.py#L32-L62).

### Running tests

Install development dependencies and run the test suite with pytest:

```
poetry install --with dev
poetry run pytest
```

## Usage

### Authentication

The API uses JWT tokens. Obtain a token by sending a `POST` request to
`/login` with `username` and `password` form fields. On success the
endpoint returns a bearer
token[\[15\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/routes/login.py#L22-L56):

```
curl -X POST \
  http://localhost:8000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword"
```

### Create user

An authenticated administrator can create new users by sending a `POST`
request to `/users` with a JSON body containing `username`, `password`
and `role` == `admin`[\[16\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/routes/users.py#L19-L39).
The response returns the created user's public data.

```
curl -X POST \
  http://localhost:8000/users \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"username": "jane", "password": "secret", "role": "user"}'
```

### Health check

A simple `GET /health` endpoint is provided to check the service status.
It returns `{ "status": "ok" }` when the service is
running[\[17\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/main.py#L29-L32).

## Running with Docker Compose

To run the application together with PostgreSQL using Docker Compose:

1.  **Build the application image**

Use the provided `ci-cd/Dockerfile` to build the image:

```
docker build -t fastapi_ddd_template_app:0.1.0 -f ci-cd/Dockerfile .
```

2.  **Generate or edit the compose file**

A ready‑made `deploy/docker-compose.yml` is included. If you change
configuration variables or secrets, regenerate it by running:

```
python ci-cd/generate_compose.py \
  --image fastapi_ddd_template_app:0.1.0 \
  --config-fields deploy/config_fields.json \
  --template ci-cd/compose.tpl.json \
  --output deploy/docker-compose.yml
```

3.  **Prepare secrets**

Create a `deploy/secrets/` directory and add files for the secrets
defined in `config_fields.json`. The file names must be the lower‑case
versions of the environment variables marked as secrets, and their
contents should be the secret values. For example:

-   `deploy/secrets/fastapi_ddd_template_jwt_secret` -- contents: your
    JWT secret

-   `deploy/secrets/fastapi_ddd_template_postgres_user_secret` --
    contents: database user password

-   `deploy/secrets/fastapi_ddd_template_app_admin_password_hash` --
    contents: bcrypt hash for the admin user

4.  **Run**

```
cd deploy
docker compose up -d
```

The compose file defines services for the database, a one‑time bootstrap
container that runs migrations and optionally creates the admin user,
and the application
itself[\[11\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/deploy/docker-compose.yml#L1-L80).
Environment variables are passed through and secrets are mounted as
files to `/run/secrets` inside the container.

## CI/CD pipeline (tests, linting etc. is skipped intentionally)

The repository includes tooling to automate building and deploying the application as part of a continuous integration/continuous deployment (CI/CD) workflow. The pipeline involves the following steps:

### 1. In Development: Prepare configuration files

Prepare configuration files for the CI/CD pipeline:

```
python -m app.scripts.generate_config_fields --output deploy/config_fields.json
```

This generates `deploy/config_fields.json` from the settings class and should be committed along with `pyproject.toml` and `poetry.lock` to ensure the CI can build a deterministic image. This file lists all environment variables and identifies which ones should be treated as secrets.

### 2. In CI/CD: Build and save docker image

Build the container image and save it to a compressed tarball:

```
docker buildx build --tag fastapi_ddd_template_app:0.1.0 . --file ./ci-cd/Dockerfile
docker save fastapi_ddd_template_app:0.1.0 | gzip > ./deploy/fastapi_ddd_template_app:0.1.0.tar.gz
```

The resulting `fastapi_ddd_template_app:0.1.0.tar.gz` can then be transferred to the deployment host.

### 3. In CI/CD: Generate compose manifest

Generate `deploy/docker-compose.yml` based on your configuration:

```
python ./ci-cd/generate_compose.py --image fastapi_ddd_template_app:0.1.0 --output ./deploy/docker-compose.yml
```

### 4. On host: Load image

Copy the compressed image archive to the target host and load it into the local Docker registry:

```
gunzip -c fastapi_ddd_template_app:0.1.0.tar.gz | docker load
```

### 5. On host: Create compose secrets

Automatically create the secret files expected by the compose file using the provided script. Values can be supplied via the existing `config_fields.json` file or via the command line:

```
python ./deploy/create_compose_secrets.py
```

This script creates files in the `deploy/secrets` directory with names matching the lower‑cased secret variables.

### 6. On host: Deploy the stack

Start the services using Docker Compose with your production environment file:

```
docker compose --env-file ./deploy/.env.prod -f ./deploy/docker-compose.yml up -d
```

The application will start after the database is healthy and migrations have run. Ensure that `.env.prod` contains the correct values for all variables listed in `config_fields.json`.

## Environment variables

The project reads configuration from environment variables prefixed with
`FASTAPI_DDD_TEMPLATE_`[\[18\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/config/config.py#L10-L42).
Important variables include:

| Variable | Description | Example |
|----------|-------------|---------|
| `FASTAPI_DDD_TEMPLATE_ENV` | Environment (`dev`, `test`, `prod`) | `dev` |
| `FASTAPI_DDD_TEMPLATE_DEBUG` | Enable debug mode (must be `true` in development) | `true` |
| `FASTAPI_DDD_TEMPLATE_JWT_SECRET` | Secret used to sign JWT tokens | `change_me` |
| `FASTAPI_DDD_TEMPLATE_POSTGRES_DRIVER` | Database driver (`postgresql+asyncpg` or `postgresql+psycopg`) | `postgresql+asyncpg` |
| `FASTAPI_DDD_TEMPLATE_POSTGRES_USER` | Database user | `postgres` |
| `FASTAPI_DDD_TEMPLATE_POSTGRES_USER_SECRET` | Password for the database user | (secret) |
| `FASTAPI_DDD_TEMPLATE_POSTGRES_DB` | Database name | `fastapi_ddd_template_dev_db` |
| `FASTAPI_DDD_TEMPLATE_POSTGRES_HOST` | Database host | `localhost` |
| `FASTAPI_DDD_TEMPLATE_UVICORN_PORT` | Port on which Uvicorn will listen | `8000` |
| `FASTAPI_DDD_TEMPLATE_APP_BOOTSTRAP_ADMIN` | Whether to run the admin creation script at startup | `false` |
| `FASTAPI_DDD_TEMPLATE_APP_ADMIN` | Username for the admin account | `admin` |
| `FASTAPI_DDD_TEMPLATE_APP_ADMIN_PASSWORD_HASH` | Bcrypt hash for the admin password | (secret) |

See `.env_example.dev` and `.env_example.prod` for full examples of
these
variables[\[9\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/.env_example.dev#L1-L19)[\[10\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/deploy/.env_example.prod#L1-L15).

## Contributing

Contributions to improve or extend this template are welcome. Please
open an issue or submit a pull request.

## License

This project is released under the MIT
License[\[19\]](https://github.com/kaxcheg/FastAPI-DDD-template#:~:text=).

[\[1\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/domain/entities/user/user.py#L22-L25)
user.py

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/domain/entities/user/user.py>

[\[2\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/domain/value_objects/user_id.py#L1-L48)
user_id.py

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/domain/value_objects/user_id.py>

[\[3\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/domain/value_objects/user_role.py#L1-L6)
user_role.py

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/domain/value_objects/user_role.py>

[\[4\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/application/use_cases/create_user.py#L54-L69)
create_user.py

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/application/use_cases/create_user.py>

[\[5\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/application/use_cases/authenticate_user.py#L38-L65)
authenticate_user.py

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/application/use_cases/authenticate_user.py>

[\[6\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/routes/users.py#L19-L42)
[\[16\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/routes/users.py#L19-L39)
users.py

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/routes/users.py>

[\[7\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/routes/login.py#L22-L55)
[\[15\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/routes/login.py#L22-L56)
login.py

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/routes/login.py>

[\[8\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/config/config.py#L21-L45)
[\[18\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/config/config.py#L10-L42)
config.py

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/config/config.py>

[\[9\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/.env_example.dev#L1-L19)
.env_example.dev

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/.env_example.dev>

[\[10\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/deploy/.env_example.prod#L1-L15)
.env_example.prod

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/deploy/.env_example.prod>

[\[11\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/deploy/docker-compose.yml#L1-L80)
docker-compose.yml

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/deploy/docker-compose.yml>

[\[12\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/scripts/create_admin.py#L32-L43)
[\[14\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/scripts/create_admin.py#L32-L62)
create_admin.py

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/scripts/create_admin.py>

[\[13\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/application/dto/dto.py#L6-L28)
dto.py

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/application/dto/dto.py>

[\[17\]](https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/main.py#L29-L32)
main.py

<https://github.com/kaxcheg/FastAPI-DDD-template/blob/d2bcae82596bcab54db2df92acfa8f5239a7dec3/app/interface/http/main.py>

[\[19\]](https://github.com/kaxcheg/FastAPI-DDD-template#:~:text=)
GitHub - kaxcheg/FastAPI-DDD-template: Example of DDD architecture with
User entity and create_user use case

<https://github.com/kaxcheg/FastAPI-DDD-template>