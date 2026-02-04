# Backend Tests

This directory contains all test files for the backend application.

## Structure

```
tests/
├── __init__.py
├── services/
│   ├── __init__.py
│   └── test_strategy_engine.py
├── test_gemini_image.py          # Image generation tests
├── test_gemini_http.py           # HTTP API tests
└── test_mock_api.py              # Mock API tests
```

## Running Tests

### Run all tests:
```bash
pytest tests/
```

### Run specific test file:
```bash
pytest tests/test_gemini_image.py
```

### Vertex AI behavior (URL / systemInstruction / location):
```bash
# With pytest (recommended)
pytest tests/test_gemini_vertex_behavior.py -v

# Without pytest (from backend env with deps)
cd backend && PYTHONPATH=. python scripts/run_vertex_behavior_tests.py
```

### Run with coverage:
```bash
pytest tests/ --cov=app --cov-report=html
```

## Test Categories

- **Unit Tests**: `tests/services/` - Test individual service classes
- **Integration Tests**: `test_*.py` - Test API endpoints and external integrations

