"""Tests for market chain endpoint with Tiger service mocked."""

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from app.main import app
from app.api.deps import get_current_user
from app.services.tiger_service import tiger_service


def _override_get_current_user():
    """Return a mock authenticated user."""
    user = MagicMock()
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.is_pro = True
    return user


def test_market_chain_with_tiger_mock():
    """Verify market chain endpoint uses mocked Tiger response."""
    app.dependency_overrides[get_current_user] = _override_get_current_user

    mock_chain = {
        "calls": [
            {"strike": 100, "bid": 1.0, "ask": 1.1, "implied_volatility": 0.25},
        ],
        "puts": [
            {"strike": 100, "bid": 1.2, "ask": 1.3, "implied_volatility": 0.28},
        ],
        "spot_price": 101.5,
        "_source": "mock",
    }

    async def _mock_get_option_chain(*args, **kwargs):
        return mock_chain

    tiger_service.get_option_chain = AsyncMock(side_effect=_mock_get_option_chain)

    client = TestClient(app)
    response = client.get(
        "/api/v1/market/chain",
        params={"symbol": "AAPL", "expiration_date": "2025-01-17"},
        headers={"Authorization": "Bearer test"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "AAPL"
    assert data["spot_price"] == 101.5
    assert len(data["calls"]) == 1
    assert len(data["puts"]) == 1

    app.dependency_overrides.clear()
