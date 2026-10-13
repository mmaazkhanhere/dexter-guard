# Spec 009 deployment decision

The repository uses the current Vercel Services topology: a Vite web service at
the root URL and a FastAPI service routed under `/api`. The backend keeps the
original `/api/v1/*` path, so the browser calls same-origin `/api/v1/*` routes.

The configuration is in [`vercel.json`](../../vercel.json). The Python entrypoint
is [`backend/main.py`](../../backend/main.py), which imports the composed app
from `src/app` and does not expose credentials to the browser.

The topology is feasible but not production-verified in this workspace. Vercel
Services is currently Beta and requires the project framework to be set to
Services. Vercel project access, plan limits, database credentials, and LLM
provider secrets were not available, so no deployment URL is claimed.

Official references reviewed on 2026-10-13:

- [Vercel Services](https://vercel.com/docs/services) — `services` configuration, rewrites, and one-deployment routing.
- [Services routing and communication](https://vercel.com/docs/services/routing) — the backend receives the original `/api/...` path.
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes) — FastAPI is supported as an ASGI application.
- [Function duration](https://vercel.com/docs/functions/configuring-functions/duration) — Python duration is configured in deployment configuration and remains plan-bounded.

Known deployment gates:

- Set the Vercel project framework to Services and grant Services Beta access if the project does not already have it.
- Provision PostgreSQL and configure `DATABASE_URL`; the current local SQLite repositories are not valid deployed persistence.
- Configure server-only LLM variables and verify provider timeout is below the selected function limit.
- Run `vercel build`, preview smoke tests, and persistence/reload checks before production promotion.
