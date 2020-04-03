from decimal import Decimal as D
import secrets

import pytest

from aioxrpy.serializer import (
    serialize, deserialize, lookup_field, BlobSerializer, AmountSerializer,
    PathSetSerializer, ArraySerializer
)
from aioxrpy.definitions import RippleTransactionType, RIPPLE_FIELDS


def test_transactions():
    expected_binary = (
        b"\x12\x00\x00$\x00\x00\x00\x01a\xd6\x87\x1a\xfdI\x8d\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00USD\x00\x00\x00\x00\x00U\x0f"
        b"\xc6 \x03\xe7\x85\xdc#\x1a\x10X\xa0^V\xe3\xf0\x9c\xf4\xe6h@\x00\x00"
        b"\x00\x00\x00\x00\n\x81\x14P\xf9z\x07/\x1cCW\xf1\xad\x84Vj`\x94y\xd9"
        b"'\xc9B\x83\x14U\x0f\xc6 \x03\xe7\x85\xdc#\x1a\x10X\xa0^V\xe3\xf0"
        b"\x9c\xf4\xe6"
    )
    expected_dict = {
        "TransactionType": RippleTransactionType.Payment,
        "Account": "r3P9vH81KBayazSTrQj6S25jW6kDb779Gi",
        "Destination": "r3kmLJN5D28dHuH8vZNUZpMC43pEHpaocV",
        "Amount": {
            "value": 200000000,
            'issuer': 'r3kmLJN5D28dHuH8vZNUZpMC43pEHpaocV',
            'code': 'USD'
        },
        "Fee": 10,
        "Sequence": 1
    }

    assert serialize(expected_dict) == expected_binary
    assert deserialize(expected_binary) == expected_dict


def test_field_lookup():
    for field in RIPPLE_FIELDS.values():
        if not field.is_serialized:
            continue

        field_id = field.field_id
        length, looked_up_field = lookup_field(field_id)
        assert looked_up_field == field
        assert len(field_id) == length


def test_simple_test():
    expected_dict = {
        'Account': 'r3P9vH81KBayazSTrQj6S25jW6kDb779Gi',
        'Destination': 'r3kmLJN5D28dHuH8vZNUZpMC43pEHpaocV',
        'TransactionType': RippleTransactionType.Payment,
        'Sequence': 1,
        'Fee': 10
    }
    serialized = serialize(expected_dict)
    deserialized = deserialize(serialized)
    assert deserialized == expected_dict


def test_blob_serializer():
    serializer = BlobSerializer()

    # payloads with length <= 192
    payload = secrets.randbits(192 * 8).to_bytes(192, 'big')
    serialized = serializer.serialize(payload)
    length, deserialized = serializer.deserialize(serialized)
    assert deserialized == payload
    assert length == 192 + 1

    # payloads with length <= 12480
    payload = secrets.randbits(12480 * 8).to_bytes(12480, 'big')
    serialized = serializer.serialize(payload)
    length, deserialized = serializer.deserialize(serialized)
    assert deserialized == payload
    assert length == 12480 + 2

    # payloads with length <= 918744
    payload = secrets.randbits(918744 * 8).to_bytes(918744, 'big')
    serialized = serializer.serialize(payload)
    length, deserialized = serializer.deserialize(serialized)
    assert deserialized == payload
    assert length == 918744 + 3

    # too long payloads
    payload = secrets.randbits(918745 * 8).to_bytes(918745, 'big')
    with pytest.raises(ValueError):
        serializer.serialize(payload)


def test_amount_serializer_scale_to_xrp():
    serializer = AmountSerializer()
    known_good_results = {
        '1': (0, 1000000000000000, -15),
        '-1': (1, 1000000000000000, -15),
        '9999': (0, 9999000000000000, -12),
        '0.1': (0, 1000000000000000, -16),
        '0.099': (0, 9900000000000000, -17),
        '1000.0001000': (0, 1000000100000000, -12),
        '1000.1000000': (0, 1000100000000000, -12)
    }
    for value, result in known_good_results.items():
        assert serializer.scale_to_xrp_amount(D(value)) == result

    # Min valid exp is 96, (96 - 15) + 1 is 82
    assert serializer.scale_to_xrp_amount(9 * (D(10) ** -82)) == (False, 0, 0)

    with pytest.raises(ValueError):
        # Max valid exp is 80, (80 + 15) +1 is 96
        serializer.scale_to_xrp_amount(9 * (D(10) ** 96))


def test_amount_serializer_issued_currency():
    serializer = AmountSerializer()
    issued_currency = {
        'issuer': 'r3kmLJN5D28dHuH8vZNUZpMC43pEHpaocV',
        'code': 'USD'
    }

    # zero
    expected_binary = (
        b'\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00USD\x00\x00\x00\x00\x00U\x0f\xc6 \x03\xe7\x85\xdc#\x1a'
        b'\x10X\xa0^V\xe3\xf0\x9c\xf4\xe6'
    )
    expected_value = {**issued_currency, 'value': 0}
    serialized = serializer.serialize(expected_value)
    assert serialized == expected_binary
    length, deserialized = serializer.deserialize(serialized)
    assert serializer.deserialize(serialized) == (48, expected_value)

    # positive number
    expected_binary = (
        b'\xd6\x87\x1a\xfdI\x8d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00USD\x00\x00\x00\x00\x00U\x0f\xc6 \x03\xe7\x85\xdc#\x1a'
        b'\x10X\xa0^V\xe3\xf0\x9c\xf4\xe6'
    )
    expected_value = {**issued_currency, 'value': 200000000}
    serialized = serializer.serialize(expected_value)
    assert serialized == expected_binary
    length, deserialized = serializer.deserialize(serialized)
    assert serializer.deserialize(serialized) == (48, expected_value)

    # fraction
    expected_binary = None
    expected_value = {**issued_currency, 'value': 21.37}
    serialized = serializer.serialize(expected_value)
    # assert serialized == expected_binary
    length, deserialized = serializer.deserialize(serialized)
    assert serializer.deserialize(serialized) == (48, expected_value)

    # negative number
    expected_binary = (
        b'\x96\x87\x1a\xfdI\x8d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00USD\x00\x00\x00\x00\x00U\x0f\xc6 \x03\xe7\x85\xdc#\x1a'
        b'\x10X\xa0^V\xe3\xf0\x9c\xf4\xe6'
    )
    expected_value = {**issued_currency, 'value': -200000000}
    serialized = serializer.serialize(expected_value)
    assert serialized == expected_binary
    length, deserialized = serializer.deserialize(serialized)
    assert serializer.deserialize(serialized) == (48, expected_value)


def test_amount_serializer_xrp():
    serializer = AmountSerializer()

    # positive number
    expected_value = 10**17
    expected_binary = b'AcEx]\x8a\x00\x00'
    serialized = serializer.serialize(expected_value)
    assert serialized == expected_binary
    assert serializer.deserialize(serialized) == (8, expected_value)

    # negative number
    expected_value = -10**17
    expected_binary = b'\x01cEx]\x8a\x00\x00'
    serialized = serializer.serialize(expected_value)
    assert serialized == expected_binary
    assert serializer.deserialize(serialized) == (8, expected_value)

    # invalid type
    with pytest.raises(ValueError):
        serializer.serialize('test')


def test_pathset_serializer():
    serializer = PathSetSerializer()
    expected_binary = (
        b'0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00BTC\x00\x00\x00'
        b'\x00\x00\n \xb3\xc8_H%2\xa9W\x8d\xbb9P\xb8\\\xa0e\x94\xd1\xff0\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00BTC\x00\x00\x00\x00\x00'
        b'G\xda\x9e.\x00\xec\xf2$\xa5#)y?\x1b\xb2\x0f\xb1\xb5\xead\x01G\xda'
        b'\x9e.\x00\xec\xf2$\xa5#)y?\x1b\xb2\x0f\xb1\xb5\xead\x01$^B[\xe6\xec'
        b']\x86o\xcb\xa7`\xa39C&\x14\xdcH@\xff0\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00BTC\x00\x00\x00\x00\x00G\xda\x9e.\x00\xec\xf2'
        b'$\xa5#)y?\x1b\xb2\x0f\xb1\xb5\xead\x01G\xda\x9e.\x00\xec\xf2$\xa5'
        b'#)y?\x1b\xb2\x0f\xb1\xb5\xead\x01$^B[\xe6\xec]\x86o\xcb\xa7`\xa39C&'
        b'\x14\xdcH@\x01\xa6\x9e\xfe\xe9qb&N\x8d\xff\xba5\xfcY\x8et\xf6\x1e'
        b'\xac\x8a\xff0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00BTC'
        b'\x00\x00\x00\x00\x00G\xda\x9e.\x00\xec\xf2$\xa5#)y?\x1b\xb2\x0f'
        b'\xb1\xb5\xead\x01G\xda\x9e.\x00\xec\xf2$\xa5#)y?\x1b\xb2\x0f\xb1'
        b'\xb5\xead\x01\xa7:\x0f\xb8\xc2\x03\xb40\xfc=\xd3\xd2\xf3L\x06\xeb'
        b'\xb6bL\x97\x00'
    )
    expected_pathset = [
        [
            {
                "issuer": "rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B",
                "currency": "BTC"
            }
        ],
        [
            {
                "issuer": "rfYv1TXnwgDDK4WQNbFALykYuEBnrR4pDX",
                "currency": "BTC"
            },
            {
                "account": "rfYv1TXnwgDDK4WQNbFALykYuEBnrR4pDX"
            },
            {
                "account": "rhKJE9kFPz6DuK4KyL2o8NkCCNPKnSQGRL"
            }
        ],
        [
            {
                "issuer": "rfYv1TXnwgDDK4WQNbFALykYuEBnrR4pDX",
                "currency": "BTC"
            },
            {
                "account": "rfYv1TXnwgDDK4WQNbFALykYuEBnrR4pDX"
            },
            {
                "account": "rhKJE9kFPz6DuK4KyL2o8NkCCNPKnSQGRL"
            },
            {
                "account": "rGUrehcNthxydn9RXg7NAFBAiCzr2gQKYQ"
            }
        ],
        [
            {
                "issuer": "rfYv1TXnwgDDK4WQNbFALykYuEBnrR4pDX",
                "currency": "BTC"
            },
            {
                "account": "rfYv1TXnwgDDK4WQNbFALykYuEBnrR4pDX"
            },
            {
                "account": "rGEDQD48uACC2JFHykNLDPj1LPuU3QsqpV"
            }
        ]
    ]
    length, deserialized = serializer.deserialize(expected_binary)
    assert length == len(expected_binary)
    assert deserialized == expected_pathset
    serialized = serializer.serialize(expected_pathset)
    assert serialized == expected_binary


def test_array_serializer():
    serializer = ArraySerializer()
    expected_binary = (
        b'\xea|\x1fhttp://example.com/memo/generic}\x04rent\xe1\xf1'
    )
    expected_array = [
        {
            "Memo": {
                "MemoType": b'http://example.com/memo/generic',
                "MemoData": b'rent'
            }
        }
    ]
    serialized = serializer.serialize(expected_array)
    assert serialized == expected_binary
    length, deserialized = serializer.deserialize(serialized)
    assert length == len(serialized)
    assert deserialized == expected_array
