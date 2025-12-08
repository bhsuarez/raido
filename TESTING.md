# Raido Testing Guide

This document provides comprehensive guidance for running and writing tests for the Raido project.

## Table of Contents

- [Test Overview](#test-overview)
- [Quick Start](#quick-start)
- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Writing Tests](#writing-tests)
- [Test Coverage](#test-coverage)
- [CI/CD Integration](#cicd-integration)

## Test Overview

Raido uses a comprehensive testing strategy with multiple test types:

### Test Types

1. **Unit Tests** - Test individual components in isolation
   - API endpoint logic
   - Database models
   - DJ Worker services
   - React components
   - Custom hooks

2. **Integration Tests** - Test component interactions
   - API + Database
   - DJ Worker + TTS services
   - Frontend + Backend API

3. **End-to-End Tests** - Test complete user workflows
   - Track playback flow
   - Station management
   - Commentary generation

### Testing Frameworks

- **Backend (Python)**: pytest, pytest-asyncio, pytest-cov
- **Frontend (TypeScript/React)**: Vitest, React Testing Library
- **Integration**: pytest with httpx

## Quick Start

### Install Test Dependencies

**Backend:**
```bash
# API service
cd services/api
pip install -r requirements-dev.txt

# DJ Worker service
cd services/dj-worker
pip install -r requirements-dev.txt
```

**Frontend:**
```bash
cd web
npm install  # Test dependencies already in package.json
```

### Run All Tests

```bash
# From project root
make test
```

## Running Tests

### All Tests

```bash
make test                    # Run all tests (backend + frontend)
```

### Backend Tests

```bash
make test-backend            # Run all backend tests
make test-api                # Run API service tests only
make test-dj-worker          # Run DJ Worker tests only
```

### Frontend Tests

```bash
make test-frontend           # Run frontend tests
make test-watch              # Run tests in watch mode (auto-reload)
```

### Integration Tests

```bash
# Start services first
make up-dev

# Run integration tests
make test-integration
```

### Unit Tests Only

```bash
make test-unit               # Run unit tests across all services
```

### Test Coverage

```bash
make test-coverage           # Generate coverage reports
```

Coverage reports are generated in:
- API: `services/api/htmlcov/index.html`
- DJ Worker: `services/dj-worker/htmlcov/index.html`
- Frontend: `web/coverage/index.html`

## Test Structure

### Backend Test Structure

```
services/api/tests/
├── conftest.py              # Shared fixtures
├── test_models.py           # Database model tests
├── test_tracks_endpoint.py  # Tracks API tests
├── test_stations_endpoint.py # Stations API tests
├── test_now_playing_endpoint.py # Now playing tests
└── ...

services/dj-worker/tests/
├── conftest.py              # Shared fixtures
├── test_commentary_generator.py # Commentary tests
├── test_tts_service.py      # TTS service tests
└── ...
```

### Frontend Test Structure

```
web/src/__tests__/
├── NowPlaying.test.tsx      # Component tests
├── RadioPlayer.test.tsx     # Player component tests
├── useNowPlaying.test.ts    # Hook tests
└── ...

web/src/test/
└── setup.ts                 # Test setup and mocks
```

### Integration Tests

```
tests/
├── __init__.py
└── test_integration.py      # End-to-end integration tests
```

## Writing Tests

### Backend Unit Tests (pytest)

**Example: Testing an API endpoint**

```python
import pytest
from httpx import AsyncClient

@pytest.mark.unit
async def test_list_tracks(client: AsyncClient, sample_tracks):
    """Test tracks listing endpoint."""
    response = await client.get("/api/v1/tracks/")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == len(sample_tracks)
    assert all("title" in track for track in data)
```

**Example: Testing a service**

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.unit
async def test_commentary_generation(mock_openai_client):
    """Test commentary generation with OpenAI."""
    generator = CommentaryGenerator()
    generator.openai_client = mock_openai_client

    result = await generator.generate("Test Song", "Test Artist")
    assert result is not None
    assert len(result) > 0
```

### Frontend Tests (Vitest + React Testing Library)

**Example: Testing a React component**

```typescript
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import NowPlaying from '@/components/NowPlaying'

describe('NowPlaying Component', () => {
  it('renders track information', () => {
    const mockData = {
      track: { title: 'Test Song', artist: 'Test Artist' }
    }

    render(<NowPlaying data={mockData} />)

    expect(screen.getByText('Test Song')).toBeInTheDocument()
    expect(screen.getByText('Test Artist')).toBeInTheDocument()
  })
})
```

**Example: Testing a custom hook**

```typescript
import { renderHook, waitFor } from '@testing-library/react'
import { useNowPlaying } from '@/hooks/useNowPlaying'

describe('useNowPlaying Hook', () => {
  it('fetches now playing data', async () => {
    const { result } = renderHook(() => useNowPlaying())

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })

    expect(result.current.data).toBeDefined()
  })
})
```

### Integration Tests

**Example: Testing API integration**

```python
import pytest
import httpx

@pytest.mark.integration
async def test_track_play_flow():
    """Test complete track play flow."""
    async with httpx.AsyncClient() as client:
        # Get now playing
        response = await client.get("http://localhost:8001/api/v1/now/")
        assert response.status_code == 200

        # Verify track data
        data = response.json()
        assert "track" in data
```

## Test Markers

Backend tests use pytest markers for categorization:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (require services)
- `@pytest.mark.slow` - Slow-running tests
- `@pytest.mark.database` - Tests requiring database
- `@pytest.mark.ai` - Tests requiring AI services

**Run specific markers:**

```bash
# Run only unit tests
pytest -v -m unit

# Run only integration tests
pytest -v -m integration

# Exclude slow tests
pytest -v -m "not slow"
```

## Best Practices

### General

1. **Write tests first** (TDD) when adding new features
2. **Keep tests isolated** - Each test should be independent
3. **Use descriptive names** - Test names should explain what they test
4. **Mock external services** - Don't rely on external APIs in unit tests
5. **Test edge cases** - Not just happy paths

### Backend

1. **Use fixtures** for common test data
2. **Test async functions** with `async def test_*`
3. **Mock database** for unit tests, use real DB for integration
4. **Test error handling** - Verify exceptions and error responses
5. **Check status codes** - Always verify HTTP response codes

### Frontend

1. **Test user interactions** - Click, type, submit
2. **Test accessibility** - Use semantic queries
3. **Mock API calls** - Don't make real HTTP requests
4. **Test loading states** - Verify loading indicators
5. **Test error states** - Verify error messages display

## Continuous Integration

### Running Tests in CI

Tests can be run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Backend Tests
  run: |
    docker compose up -d db
    docker compose run api pytest tests/ -v --cov=app

- name: Run Frontend Tests
  run: |
    cd web
    npm install
    npm run test
```

### Pre-commit Hooks

Set up pre-commit hooks to run tests before commits:

```bash
# .git/hooks/pre-commit
#!/bin/bash
make test-unit
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

## Test Fixtures

### Backend Fixtures (conftest.py)

Common fixtures available in all backend tests:

- `async_session` - Database session
- `client` - Async HTTP client
- `sample_track` - Sample track data
- `sample_station` - Sample station data
- `sample_tracks` - Multiple track records
- `dj_settings` - DJ configuration

### Frontend Test Setup

Global mocks and setup in `web/src/test/setup.ts`:

- React Hot Toast mocked
- Jest DOM matchers available
- Global test utilities

## Troubleshooting

### Tests Not Running

**Issue**: Tests don't run in Docker containers

**Solution**: Ensure test dependencies are installed:
```bash
docker compose exec api pip install -r requirements-dev.txt
```

### Database Errors

**Issue**: Database connection errors in tests

**Solution**: Tests use in-memory SQLite by default. Check conftest.py configuration.

### Frontend Import Errors

**Issue**: Module not found errors in frontend tests

**Solution**: Check Vitest config and path aliases:
```bash
cd web
npm install
```

### Integration Tests Fail

**Issue**: Integration tests fail with connection errors

**Solution**: Ensure services are running:
```bash
make up-dev
make health
```

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

## Contributing

When contributing code:

1. Write tests for new features
2. Update existing tests when modifying functionality
3. Ensure all tests pass before submitting PR
4. Aim for >80% code coverage
5. Document complex test scenarios

---

For questions or issues with testing, please open a GitHub issue or consult the main [README.md](README.md).
