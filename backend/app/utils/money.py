from decimal import Decimal, ROUND_HALF_UP

TWO_DP = Decimal("0.01")


def q(value: Decimal) -> Decimal:
    return value.quantize(TWO_DP, rounding=ROUND_HALF_UP)
