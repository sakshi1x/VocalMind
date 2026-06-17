# API Key Authentication & Management Design

## Overview

This document describes the recommended architecture and implementation for secure API key authentication and management in the Sentiment Grievance System. It covers ORM model design, FastAPI dependency, secure key generation, storage, and operational best practices, tailored to the current multi-service, SQLAlchemy/PostgreSQL-based microservices architecture.

---

## 1. API Key Model Design

- **Table:** `api_keys`
- **Fields:**
  - `id`: Integer, primary key, auto-increment
  - `identifier`: String, human-readable label for the key (e.g., service name)
  - `api_key_hash`: String, SHA-256 hash of the raw API key (never store raw keys)
  - `is_active`: Boolean, enables/disables the key
  - `expires_on`: DateTime (optional), expiry timestamp
  - `created_at`: DateTime, creation timestamp
  - `last_used_at`: DateTime, updated on each use
  - `user_id`: String, user identity (optional, for audit/multi-user)
  - `tenant_id`: String, tenant/org identity (for multi-tenancy)
  - `scopes`: String (JSON or comma-separated), allowed actions/roles
  - `rate_limit`: Integer, per-key rate limiting
- **ORM:** Use SQLAlchemy declarative base, as in `shared/database/base.py`.
- **Security:**
  - Store only the hash, never the raw key.
  - Use strong, random keys (≥ 32 bytes, hex-encoded).

---

## 2. API Key Generation

- **Script:** Provide a CLI tool (e.g., `scripts/generate_api_key.sh`) to generate, hash, and insert keys.
- **Process:**
  1. Generate a random key (e.g., `openssl rand -hex 24`)
  2. Hash with SHA-256
  3. Insert into `api_keys` table with identifier and optional expiry
  4. Display the raw key ONCE to the operator
- **Best Practices:**
  - Never log or store the raw key after creation
  - Use environment variables for DB credentials

---

## 3. Authentication Dependency (FastAPI)

- **Dependency:** Implement a FastAPI dependency (`verify_api_key`) that:
  1. Extracts the `X-API-Key` header
  2. Hashes the provided key
  3. Looks up the hash in the DB (active, not expired)
  4. Updates `last_used_at` on success
  5. Raises `401 Unauthorized` on failure
  6. Returns an `AuthContext` object with `user_id`, `tenant_id`, `scopes`, `api_key_id`, and `identifier` for downstream propagation
- **Usage:** Add as a dependency to protected routes/services
- **Logging:** Log successful authentications (never log raw keys)

### API Key Creation Request

- `POST /auth/api-key` accepts an optional JSON body with `expires_in_days`
- Example:
  ```json
  {
    "expires_in_days": 30
  }
  ```
- If `expires_in_days` is omitted, the key does not expire
- `expires_in_days` must be greater than `0`
- The server converts `expires_in_days` into a concrete `expires_on` datetime before saving to the database
- The response includes the raw `api_key` and stored `expires_on`
- `last_used_at` is internal metadata and is updated automatically when the `X-API-Key` header is validated

---

## 4. Database & Session Management

- **Session:** Use a per-request DB session (see `get_db`)
- **Engine:** Use synchronous SQLAlchemy engine for API key checks
- **Migration:** Ensure `api_keys` table is included in Alembic migrations

---

## 5. Security & Operational Best Practices

- **Key Storage:** Only store hashes, never raw keys
- **Key Rotation:** Support key expiry and deactivation
- **Audit:** Log usage (identifier, timestamp), monitor for abuse
- **Access:** Restrict key generation to trusted operators
- **Transport:** Always use HTTPS for API traffic
- **Environment:** Store DB credentials and secrets in `.env` or secret manager

---

## 6. Folder Structure & Integration

- **Model:** `services/auth-service/app/api_keys.py` (or `models.py`)
- **Dependency:** `services/auth-service/app/jwt.py` or `dependencies.py`
- **Script:** `scripts/generate_api_key.sh`
- **Docs:** This file (`docs/api-key-auth.md`)

---

## 7. Example Usage & Auth Context Propagation

- **API:**
  - Add `Depends(verify_api_key)` to FastAPI routers
  - Use `curl -H 'X-API-Key: <RAW_KEY>' ...` for requests
  - The dependency returns an `AuthContext` object, which should be passed through all service calls, pipelines, and event payloads:
    ```python
    def run_pipeline(input, context: AuthContext):
        ...
    # Example event payload:
    event = {
        "request_id": ...,  # traceable
        "user_id": context.user_id,
        "tenant_id": context.tenant_id,
        "scopes": context.scopes,
        "payload": {...}
    }
    ```
- **Key Generation:**
  - Run `./scripts/generate_api_key.sh <identifier> [expires_days]`

---

## 8. References

- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [FastAPI Security Docs](https://fastapi.tiangolo.com/advanced/security/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)

---

## 9. Sample Code References

- See `services/auth-service/app/api_keys.py` for model & dependency
- See `scripts/generate_api_key.sh` for key generation

---

## 10. Future Improvements

- Enforce tenant_id and scopes in all downstream services and DB queries (e.g., `WHERE tenant_id = :tenant_id`)
- Add service-to-service authentication (internal API keys or JWT)
- Secure message broker with per-service credentials and permissions
- Add admin UI for key management
- Implement rate limiting per key
- Add key usage analytics
- Support for JWT or OAuth2 if needed

---

**Contact:** System Architect, Sentiment Grievance System
