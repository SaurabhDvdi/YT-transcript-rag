## Summary of Changes

<!-- Provide a brief description of the problem solved and the technical approach taken. -->

## Quality & Testing Checklist

<!-- Mark completed items with [x] -->

- [ ] Backend tests pass (`cd apps/backend && uv run pytest tests/ -v`)
- [ ] Backend types pass (`cd apps/backend && uv run mypy src evaluation`)
- [ ] Backend lint passes (`cd apps/backend && uv run ruff check . && uv run ruff format --check .`)
- [ ] Frontend tests pass (`npm run test:extension`)
- [ ] Monorepo typecheck passes (`npm run typecheck`)
- [ ] Frontend lint passes (`npm run lint && npm run format`)
- [ ] Chrome MV3 build passes (`npm run build`)
- [ ] Firefox build passes (`npm run build:firefox`)

## Security & Architectural Impact

- [ ] No hardcoded secrets, credentials, or development API keys added.
- [ ] No remote scripts, `eval()`, or unvetted external dependencies introduced.
- [ ] CORS policies and authorization boundaries remain strictly enforced.
- [ ] Database migrations are backwards-compatible and additive.

## Screenshots / Verification

<!-- If this PR changes user-facing UI in the extension, attach screenshots or recordings. -->
