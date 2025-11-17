# dddapitpl

**dddapitpl** is a sample project that demonstrates how to
organise a FastAPI application using SOLID and Domain‑Driven Design (DDD)
principles. It is built with FastAPI, SQLAlchemy and Pydantic and
provides a minimal yet complete example of how to structure a service
with clear boundaries between the domain, application, infrastructure
and interface layers. The project centres around a simple user domain
with two use cases: user creation and user authentication. The project 
includes Docker Compose deployment solution for local dev, GitHub 
AWS deployment workflows.

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
    Example `.env` files for development are provided to
    help you get started.
-   **Database migrations** -- Alembic is configured for schema
    migrations; an example migration creating the `users` table is
    included.
-   **Admin bootstrapping script** -- a helper script `bootstrap.py`
    can create an initial administrator account using environment
    variables if the bootstrap flag is enabled.
-   **Docker and Docker Compose** -- a container image
    can be built via the provided `Dockerfile`, and `docker‑compose.yml` for running
    the app together with PostgreSQL for local development.
-   **AWS deployment** -- CI/CD pipelines for automatic build, testing, and deployment in AWS 
    using unified Helm manifests for three environments — CI-runner (fast deployment, 
    stateless Postgres), staging (statefulset Postgres in Pod), and production (RDS).
-   **CI pipelines** --  for running linters, unit, and integration tests for checking 
    pull requests and pushes to feature/* branches. Triggers in CI/CD: deployment to staging 
    on push to release/* branch, deployment to production on vX.Y.Z tag, ensuring compliance 
    with GitFlow practice.

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
git clone https://github.com/kaxcheg/dddapitpl.git
cd dddapitpl
```

### Running in local development environment
```
make build
make up
```
Run with provided VS Code configuration in ./vscode or another IDE with debugpy connection.
See ./dev/env.dev for config.

### Running in CI/CD
In .github/workflows there are several workflows for automatic build, testing, and deployment 
in AWS or GitHub runner using unified Helm manifests for three environments — CI-runner (fast deployment, stateless 
Postgres), staging (statefulset Postgres in Pod), and production (RDS). Configure "ci-runner" 
environment in GitHub and vars and secrets in

GitHub:

"ci-runner" environment secrets:
```
BOOTSTRAP_ADMIN_PASSWORD_HASH
DB_ADMIN_SECRET
DB_USER_SECRET
JWT_SECRET
```

"ci-runner" environment vars:
```
AWS_ACCOUNT_ID
AWS_REGION
ECR_REPOSITORY
EIP_ALLOCATION_ID
SECURITY_GROUP_ID
```

repository secret
```
AWS_ROLE_TO_ASSUME - ARN of AWS IAN role
```

AWS secrets:
```
STAGING_BOOTSTRAP_ADMIN_PASSWORD_HASH
STAGING_JWT_SECRET
STAGING_DB_USER_SECRET
STAGING_DB_ADMIN_SECRET
PROD_DB_ADMIN_SECRET
PROD_DB_USER_SECRET
PROD_JWT_SECRET
PROD_BOOTSTRAP_ADMIN_PASSWORD_HASH
```

Triggers for running are configured for deployment to staging on push to release/* branches, 
deployment to production on vX.Y.Z tag, ensuring compliance with GitFlow practice.
Release to CI runner workflow can be run manually.

### Running tests

Install development dependencies and run the test suite with pytest:

```bash
poetry install --with dev

# Run only unit tests (fast, no Docker required)
poetry run pytest tests/unit -v

# Run only integration tests (requires Docker)
poetry run pytest tests/integration -v
```

**Note**: Integration tests require Docker to be running, as they use testcontainers to spin up a PostgreSQL instance. See [tests/integration/README.md](tests/integration/README.md) for more details.

## Usage

### Authentication

The API uses JWT tokens and session ids. Obtain a token by sending a `POST` request to
`/login` with `username` and `password` form fields. On success the
endpoint returns a bearer token and session_id cookie:

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

## Contributing

Contributions to improve or extend this template are welcome. Please
open an issue or submit a pull request.

## License

This project is released under the MIT License.