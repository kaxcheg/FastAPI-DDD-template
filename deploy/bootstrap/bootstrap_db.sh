#!/usr/bin/env bash
# Initialises a PostgreSQL instance by waiting for availability, 
# creating the target role / database / schema, adjusting ownership, and enabling optional extensions.

set -euo pipefail

# --- Config from env ---
: "${DB_HOST:?missing}"
: "${DB_ADMIN:?missing}"
: "${DB_PATH:?missing}" 
: "${DB_USER:?missing}"

# Optional: app password secret file and admin password secret file
DB_ADMIN_PWD_FILE="${DB_ADMIN_PWD_FILE:-/run/secrets/db_admin_secret}"
DB_USER_PWD_FILE="${DB_USER_PWD_FILE:-/run/secrets/db_user_secret}"
DB_PORT="${DB_PORT:-5432}"
DB_TABLE_SCHEMA="${DB_TABLE_SCHEMA:-fastapi_ddd_template}"
EXTENSIONS="${DB_EXTENSIONS:-}"  # e.g. "pgcrypto,uuid-ossp"

# --- Read secrets from files if present ---
read_secret() {
  local f="$1"
  [[ -f "$f" ]] && tr -d '\r' < "$f" | sed -e 's/[[:space:]]*$//'
}

export PGPASSWORD="$(read_secret "$DB_ADMIN_PWD_FILE" || echo '')" # for psql, createdb, pg_isready

# --- Wait for server readiness ---
echo "[bootstrap] waiting for ${DB_HOST}:${DB_PORT} ..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" >/dev/null 2>&1; do
  sleep 1
done

# --- Ensure role exists (with optional password) ---
role_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -d postgres -Atc \
  "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER'")
if [[ "$role_exists" != "1" ]]; then
  echo "[bootstrap] creating role $DB_USER"
  if [[ -f "$DB_USER_PWD_FILE" ]]; then
    USER_PWD="$(read_secret "$DB_USER_PWD_FILE")"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -d postgres -v ON_ERROR_STOP=1 -c \
      "CREATE ROLE \"$DB_USER\" LOGIN PASSWORD '$(printf "%s" "$USER_PWD" | sed "s/'/''/g")';"
  else
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -d postgres -v ON_ERROR_STOP=1 -c \
      "CREATE ROLE \"$DB_USER\" LOGIN;"
  fi
else
  echo "[bootstrap] role $DB_USER already exists"
  if [[ -f "$DB_USER_PWD_FILE" ]]; then
    USER_PWD="$(read_secret "$DB_USER_PWD_FILE")"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -d postgres -v ON_ERROR_STOP=1 -v user="$DB_USER" -v pwd="$USER_PWD" <<SQL
ALTER ROLE :"user" PASSWORD :'pwd';
SQL
  fi
fi

# --- Ensure schema exists ---
psql -h "$DB_HOST" -p $DB_PORT -U "$DB_ADMIN" -d "$DB_PATH" \
  -v ON_ERROR_STOP=1 \
  -v db_user="$DB_USER" \
  -v db_schema="$DB_TABLE_SCHEMA" \
  -v db_name="$DB_PATH" <<'PSQL'   # heredoc: sends the following block to psql via stdin; single quotes prevent shell expansion

-- bash doesn't expand $, \ etc psql will do this 
-- for easier variables handling (no need to add escape chars) and executing psql metacomands (\gexec) properly.

-- 1) Create the schema if missing.
--    IF NOT EXISTS makes this statement idempotent (no error if schema already exists).
SELECT format('CREATE SCHEMA IF NOT EXISTS %I;', :'db_schema') \gexec

-- 2) Make DB_USER the owner of the schema.
--    We use format('%I', ...) to safely quote identifiers (role names) per SQL rules.
--    :'db_user' dereferences a psql variable set via "-v db_user=...".
--    \gexec takes the resulting text and executes it as SQL (dynamic SQL).
SELECT format('ALTER SCHEMA %I OWNER TO %I;', :'db_schema', :'db_user') \gexec

-- 3) Set per-database search_path for DB_USER so unqualified names resolve to "db_schema" first.
--    Again, %I safely quotes identifiers; :'db_name' is the psql variable for the database name.
--    Note: this affects NEW connections of that role to this database.
SELECT format('ALTER ROLE %I IN DATABASE %I SET search_path = %I, public;',
              :'db_user', :'db_name', :'db_schema') \gexec

PSQL

# --- Ensure $DB_USER owns and can access alembic_version ---
echo "[bootstrap] altering alembic_version owner to $DB_USER (if table exists)"
psql -h "$DB_HOST" -p $DB_PORT -U "$DB_ADMIN" -d "$DB_PATH" \
  -v ON_ERROR_STOP=1 \
  -v db_user="$DB_USER" \
  -v ver_schema="$DB_TABLE_SCHEMA" <<-'PSQL'

SELECT format('ALTER TABLE %I.%I OWNER TO %I;', :'ver_schema', 'alembic_version', :'db_user')
WHERE to_regclass(format('%I.%I', :'ver_schema', 'alembic_version')) IS NOT NULL
\gexec

PSQL

# --- Ensure $DB_PATH exists ---
db_exists=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -d postgres -Atc \
  "SELECT 1 FROM pg_database WHERE datname = '$DB_PATH'")
if [[ "$db_exists" != "1" ]]; then
  echo "[bootstrap] creating database $DB_PATH (owner: $DB_USER)"
  createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -O "$DB_USER" "$DB_PATH"
else
  echo "[bootstrap] database $DB_PATH already exists"
fi

# --- Idempotent ensure priviliges for $DB_PATH ---
current_owner=$(psql -h "$DB_HOST" -p $DB_PORT -U "$DB_ADMIN" -d postgres -Atc \
  "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = '$DB_PATH';")

if [[ "$current_owner" != "$DB_USER" ]]; then
  echo "[bootstrap] altering owner of $DB_PATH -> $DB_USER"
  psql -h "$DB_HOST" -p $DB_PORT -U "$DB_ADMIN" -d postgres -v ON_ERROR_STOP=1 -c \
    "ALTER DATABASE \"$DB_PATH\" OWNER TO \"$DB_USER\";"
else
  echo "[bootstrap] owner of $DB_PATH already $DB_USER"
fi

# --- Optional: extensions inside $DB_PATH ---
if [[ -n "$EXTENSIONS" ]]; then
  IFS=',' read -ra exts <<< "$EXTENSIONS"
  for ext in "${exts[@]}"; do
    ext="$(echo "$ext" | xargs)"
    [[ -z "$ext" ]] && continue
    echo "[bootstrap] ensure extension $ext"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_ADMIN" -d "$DB_PATH" -v ON_ERROR_STOP=1 -c \
      "CREATE EXTENSION IF NOT EXISTS \"$ext\";"
  done
fi

echo "[bootstrap] done"