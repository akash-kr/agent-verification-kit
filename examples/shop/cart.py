def total(prices, coupon=0):
    """The cart total after a percentage coupon."""
    return sum(prices) - coupon  # bug: takes 10 off, not 10%
