import pytest

from src.app.exceptions import AuthException
from src.app.models import CarClass
from src.app.security import create_token, decode_token, hash_password, verify_password
from src.app.services.pricing import calculate_price, surge_multiplier


@pytest.mark.parametrize("busy,total,expected", [(0, 10, 1.0), (4, 10, 1.0), (5, 10, 1.2), (8, 10, 1.5),
                                                  (0, 0, 1.5)])
def test_surge_multiplier(busy, total, expected):
    assert surge_multiplier(busy, total) == expected


def test_price_economy_and_minimum():
    assert calculate_price(CarClass.ECONOMY, 10, 1.0) == 239.0       # 99 + 14*10
    assert calculate_price(CarClass.ECONOMY, 1, 1.0) == 199.0        # минимальная стоимость
    assert calculate_price(CarClass.BUSINESS, 10, 1.5) == pytest.approx((299 + 320) * 1.5)


def test_password_hash_roundtrip():
    stored = hash_password("secret-123")
    assert verify_password("secret-123", stored)
    assert not verify_password("wrong", stored)
    assert hash_password("secret-123") != stored                      # соль случайная


def test_token_roundtrip_and_errors():
    token = create_token(7, "ADMIN", "k" * 32, 5)
    assert decode_token(token, "k" * 32)["sub"] == "7"
    with pytest.raises(AuthException, match="Invalid"):
        decode_token(token, "other-secret" * 3)
    with pytest.raises(AuthException, match="expired"):
        decode_token(create_token(7, "USER", "k" * 32, -1), "k" * 32)
