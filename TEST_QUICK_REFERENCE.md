# Testing Quick Reference

## Quick Commands

```bash
# Run all tests
make test

# Run specific test suites
make test-api                # API tests only
make test-dj-worker          # DJ Worker tests only
make test-frontend           # Frontend tests only
make test-integration        # Integration tests (requires services)

# Run by test type
make test-unit               # Unit tests only
make test-coverage           # Generate coverage reports

# Watch mode (frontend)
make test-watch              # Auto-reload on file changes
```

## Test File Locations

```
services/api/tests/          # API tests
services/dj-worker/tests/    # DJ Worker tests
web/src/__tests__/           # Frontend tests
tests/                       # Integration tests
```

## Writing Your First Test

### Backend (Python/Pytest)

```python
# services/api/tests/test_my_feature.py
import pytest

@pytest.mark.unit
async def test_my_feature(client):
    response = await client.get("/api/v1/my-endpoint")
    assert response.status_code == 200
```

### Frontend (TypeScript/Vitest)

```typescript
// web/src/__tests__/MyComponent.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MyComponent from '@/components/MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
```

## Common Test Patterns

### Testing API Endpoints

```python
async def test_endpoint(client, sample_track):
    # Arrange
    track_id = sample_track.id

    # Act
    response = await client.get(f"/api/v1/tracks/{track_id}")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == track_id
```

### Testing React Components

```typescript
it('handles user interaction', async () => {
  render(<MyComponent />)

  const button = screen.getByRole('button', { name: /click me/i })
  fireEvent.click(button)

  await waitFor(() => {
    expect(screen.getByText('Clicked!')).toBeInTheDocument()
  })
})
```

### Mocking API Calls

```typescript
vi.mock('@/utils/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: { message: 'success' } })
  }
}))
```

## Test Markers (Backend)

```python
@pytest.mark.unit          # Fast, isolated unit tests
@pytest.mark.integration   # Tests requiring services
@pytest.mark.slow          # Slow-running tests
@pytest.mark.database      # Tests requiring database
@pytest.mark.ai            # Tests requiring AI services
```

Run specific markers:
```bash
pytest -v -m unit
pytest -v -m "not slow"
```

## Troubleshooting

**Tests fail with import errors**
```bash
# Backend
pip install -r requirements-dev.txt

# Frontend
cd web && npm install
```

**Integration tests fail**
```bash
# Ensure services are running
make up-dev
make health
```

**Coverage reports not generating**
```bash
# Install coverage tools
pip install pytest-cov
```

## Coverage Targets

- **Minimum**: 70% overall coverage
- **Goal**: 80%+ coverage for critical paths
- **API Endpoints**: 90%+ coverage
- **Business Logic**: 85%+ coverage

## Best Practices Checklist

- [ ] Test written before/with code (TDD)
- [ ] Test name describes what it tests
- [ ] Test is isolated and independent
- [ ] External services are mocked
- [ ] Edge cases are tested
- [ ] Error cases are tested
- [ ] Test follows AAA pattern (Arrange, Act, Assert)

## Resources

- Full documentation: [TESTING.md](TESTING.md)
- Pytest: https://docs.pytest.org/
- Vitest: https://vitest.dev/
- React Testing Library: https://testing-library.com/

---

**Need help?** Check [TESTING.md](TESTING.md) for comprehensive documentation.
