#!/usr/bin/env bash
# Generate a new API key and insert it into the database.
# Usage: ./generate_api_key.sh <identifier> [expires_days]
# Example: ./generate_api_key.sh "my-app" 90
set -euo pipefail

IDENTIFIER="${1:?Usage: $0 <identifier> [expires_days]}"
EXPIRES_DAYS="${2:-}"

# Load DATABASE_URL from .env
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$SCRIPT_DIR/.env" ]]; then
  export $(grep -E '^DATABASE_URL=' "$SCRIPT_DIR/.env" | sed 's/#.*//' | xargs)
fi
DB_URL="${DATABASE_URL:?Set DATABASE_URL in .env or environment}"

# Strip async driver prefix if present (e.g. postgresql+asyncpg:// → postgresql://)
DB_URL=$(echo "$DB_URL" | sed 's|postgresql+asyncpg://|postgresql://|')

# Parse connection parts from URL for psql
DB_USER=$(echo "$DB_URL" | sed -n 's|postgresql://\([^:]*\):.*|\1|p')
DB_PASS=$(echo "$DB_URL" | sed -n 's|postgresql://[^:]*:\([^@]*\)@.*|\1|p')
DB_HOST=$(echo "$DB_URL" | sed -n 's|.*@\([^:]*\):.*|\1|p')
DB_PORT=$(echo "$DB_URL" | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
DB_NAME=$(echo "$DB_URL" | sed -n 's|.*/\([^?]*\).*|\1|p')

# Generate a random 48-char hex key
RAW_KEY=$(openssl rand -hex 24)
# SHA-256 hash
KEY_HASH=$(echo -n "$RAW_KEY" | shasum -a 256 | awk '{print $1}')

# Build SQL
NOW=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
if [[ -n "$EXPIRES_DAYS" ]]; then
  if [[ "$(uname)" == "Darwin" ]]; then
    EXPIRES=$(date -u -v+"${EXPIRES_DAYS}d" +"%Y-%m-%dT%H:%M:%SZ")
  else
    EXPIRES=$(date -u -d "+${EXPIRES_DAYS} days" +"%Y-%m-%dT%H:%M:%SZ")
  fi
  SQL="INSERT INTO api_keys (identifier, api_key_hash, is_active, expires_on, created_at) VALUES ('${IDENTIFIER}', '${KEY_HASH}', true, '${EXPIRES}', '${NOW}');"
else
  SQL="INSERT INTO api_keys (identifier, api_key_hash, is_active, created_at) VALUES ('${IDENTIFIER}', '${KEY_HASH}', true, '${NOW}');"
fi

# Execute
PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$SQL" > /dev/null

echo ""
echo "API key created successfully!"
echo "──────────────────────────────────────────"
echo " Identifier : $IDENTIFIER"
echo " API Key    : $RAW_KEY"
if [[ -n "$EXPIRES_DAYS" ]]; then
  echo " Expires    : $EXPIRES"
fi
echo "──────────────────────────────────────────"
echo ""
echo "Use it in requests as:"
echo " curl -H 'X-API-Key: $RAW_KEY' ..."
echo ""
echo "⚠ Save this key now — it cannot be retrieved later."
