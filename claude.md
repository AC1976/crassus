# Crassus Property Management Guidelines

## Tech Stack
- Framework: FastAPI (Python 3.11+)
- Database: SQLite (via Core SQLAlchemy ORM only, async session optional but preferred)
- Validation: Pydantic v2
- Resend for emailing

## Architecture & Code Style
- Follow a modular structure: `main.py`, `models.py`, `schemas.py`, `database.py`, `routers/`.
- Use explicit Pydantic schemas for request validation and response serialization.
- Always include type hints on all function signatures.
- Handle database sessions using a `get_db` dependency injection pattern.
- Always return appropriate HTTP status codes (e.g., 201 Created, 204 No Content).
- Use industry common solutions and modules where possible, do not reinvent the wheel if standard practice exists. 
- For auth, we need a robust and safe system that works only with user provided email addresses. No auth via socials.

## Common Commands
- Run dev server: `uvicorn main:app --reload`
- Code formatting: `black .`
