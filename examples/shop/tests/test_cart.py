from cart import total


def test_adds_prices():
    assert total([20, 20]) == 40
