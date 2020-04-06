from decimal import Decimal


def xrp_to_drops(amount):
    return int((Decimal(1000000) * amount).quantize(Decimal('1')))


def drops_to_xrp(amount):
    return Decimal(amount) / Decimal(1000000)
