# FastAPI DDD Template

**FastAPI‑DDD Template** is a sample project that demonstrates how to
organise a FastAPI application using SOLID and Domain‑Driven Design (DDD)
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
    role and activity flag.
    Supporting value objects encapsulate user identifiers, raw passwords
    and roles.
-   **Use cases** -- the application layer exposes explicit use cases
    for creating a user and authenticating a user. The
    `CreateUserUseCase` validates input, hashes the password, creates a
    new user via a factory method and persists it through the repository.
    The `AuthenticateUserUseCase` retrieves a user by username and
    verifies the password hash.
-   **Ports and adapters** -- clear interfaces define repositories,
    units of work, hashing services and authentication services.
    Concrete implementations in the infrastructure layer use SQLAlchemy
    for persistence and bcrypt for hashing, while JWT is used for
    issuing access tokens.
-   **Dependency injection and FastAPI integration** -- dependencies are
    provided via FastAPI `Depends` so that the HTTP layer remains thin.
    Routes for `/users` and `/login` map incoming requests to use cases
    and presenters.
-   **Asynchronous programming** -- the project uses SQLAlchemy's async
    API and asynchronous units of work, allowing non‑blocking database
    access.
-   **Configuration via environment variables** -- all configuration is
    loaded through a single Pydantic settings class with prefixes,
    supporting different environments (development, testing, production).
    Example `.env` files for development and production are provided to
    help you get started.
-   **Database migrations** -- Alembic is configured for schema
    migrations; an example migration creating the `users` table is
    included.
-   **Docker and Docker Compose** -- a production‑ready container image
    can be built via the provided `Dockerfile`, and `docker‑compose.yml` for running
    the app together with PostgreSQL. Secrets are mounted from files to
    avoid hard‑coding credentials.
-   **Admin bootstrapping script** -- a helper script `bootstrap.py`
    can create an initial administrator account using environment
    variables if the bootstrap flag is enabled.

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
    the domain from external representations.
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
secret, and server host/port.
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

To bootstrap an initial administrator, set `FASTAPI_DDD_TEMPLATE_BOOTSTRAP_FLAG=true`
and provide `FASTAPI_DDD_TEMPLATE_BOOTSTRAP_ADMIN` and `FASTAPI_DDD_TEMPLATE_BOOTSTRAP_ADMIN_PASSWORD_HASH` (bcrypt hash) in
your environment. Then run:

```
poetry run python -m app.scripts.bootstrap
```

The script will create an admin account if it does not already
exist

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
endpoint returns a bearer token:

```
curl -X POST \
  http://localhost:8000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=yourpassword"
```

### Create user

An authenticated administrator can create new users by sending a `POST`
request to `/users` with a JSON body containing `username`, `password`
and `role` == `admin`.
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
running.

## Running with Docker Compose

To run the application together with PostgreSQL using Docker Compose:

1.  **Build the application image**

Use the provided `ci-cd/Dockerfile` to build the image:

```
docker build -t fastapi_ddd_template_app:0.1.0 -f ci-cd/Dockerfile .
```

2.  **Use the included compose file**

A ready‑made `deploy/docker-compose.yml` is included. 

3.  **Create compose secrets**

Automatically create the secret files expected by the compose file using the provided script. Values can be supplied the command line or file:

```
python ./deploy/create_compose_secrets.py
```

4.  **Run**

```
docker compose --env-file ./deploy/.env.prod -f ./deploy/docker-compose.yml up -d

```

The compose file defines services for the database, a one‑time bootstrap
container that runs migrations and optionally creates the admin user,
and the application itself.
Environment variables are passed through and secrets are mounted as
files to `/run/secrets` inside the container.

## Contributing

Contributions to improve or extend this template are welcome. Please
open an issue or submit a pull request.

## License

This project is released under the MIT License.