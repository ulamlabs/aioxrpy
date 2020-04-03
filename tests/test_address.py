import pytest

from aioxrpy import address


def test_address_validation():
    with pytest.raises(ValueError):
        # Valid string but not account ID
        address.decode_address('snoPBrXtMeMyMHUVTgbuqAfg1SUTb')

    with pytest.raises(ValueError):
        address.decode_address('shitcoin1234')


def test_decode_address():
    binary = (
        b'\xb5\xf7by\x8aS\xd5C\xa0\x14\xca\xf8\xb2\x97\xcf\xf8\xf2\xf97\xe8'
    )
    base58 = 'rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh'
    assert address.decode_address(base58) == binary


def test_encode_address():
    binary = (
        b'\xb5\xf7by\x8aS\xd5C\xa0\x14\xca\xf8\xb2\x97\xcf\xf8\xf2\xf97\xe8'
    )
    base58 = 'rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh'
    assert address.encode_address(binary) == base58
