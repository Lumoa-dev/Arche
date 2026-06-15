# CI/CD Pipeline

## Pipeline Overview

Defined in `.github/workflows/ci.yml`. Stages execute in order:

```
backend-lint → backend-test → frontend-check → frontend-test → security-scan → gate → (build → deploy + tag-release)
```

| Stage | Description |
|-------|-------------|
| backend-lint | ruff check + ruff format --check + custom lint rules |
| backend-test | pytest with coverage gate (min 40%) |
| frontend-check | npm run type-check + npm run lint |
| frontend-test | npm run test:run (vitest + jsdom) |
| security-scan | Security audit |
| gate | Manual approval gate (environment) |
| build | Docker image build & push to ghcr.io |
| deploy | Deploy to production |
| tag-release | Auto-create git tag (master push only) |

## Trigger Rules

| Trigger | Actions |
|---------|---------|
| Tag `v*` | Full pipeline → build → deploy |
| PR merge to `master` | Full pipeline → auto-increment patch version → build → deploy |
| Push to `master` (no tag) | Lint/test only, no build |

## Build

Defined in `.github/workflows/build.yml`. Builds Docker image and pushes to GitHub Container Registry:

```
ghcr.io/<org>/arche:<version>
```

### Docker Compose (Production)

```
docker-compose.yml
├── nginx (reverse proxy + SSL)
├── backend
├── postgresql
└── minio
```

## Versioning

- Automatic patch version bump on PR merge to master
- Tags follow semver: `v1.2.3`
- `tag-release` job auto-creates and pushes tags on successful master builds

## Deployment

Defined in `.github/workflows/deploy.yml`. Production serves via Nginx reverse proxy.

### Environment Variables

- `.env` file for local dev
- Environment variables for CI/production
- Database config for production settings

## API Type Sync

```bash
cd frontend && npm run generate:api
# → fetches OpenAPI schema from running backend
# → generates src/services/api/generated.d.ts
```

CI verifies that the generated types file exists and is up-to-date:
```bash
test -f src/services/api/generated.d.ts
```

## Security

- Container images pushed to ghcr.io (not Docker Hub)
- PyPI uses Aliyun mirror
- No secrets committed to repository
