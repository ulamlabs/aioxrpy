from decimal import Decimal

from aioxrpy import decimals


def test_xrp_to_drops():
    assert decimals.xrp_to_drops(Decimal('123.456789')) == 123456789


def test_drops_to_xrp():
    assert decimals.drops_to_xrp(123456789) == Decimal('123.456789')
