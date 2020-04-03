from binascii import unhexlify
from abc import ABC, abstractmethod
from decimal import Decimal as D
import struct

from aioxrpy.address import encode_address, decode_address
from aioxrpy.definitions import RippleType, RIPPLE_FIELDS, RIPPLE_FIELDS_LOOKUP
from aioxrpy.exceptions import RippleSerializerUnsupportedTypeException


class BaseSerializer(ABC):
    @abstractmethod
    def serialize(self, value):
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, value):
        raise NotImplementedError


class BasicTypeSerializer(BaseSerializer):
    def __init__(self, fmt=None):
        if fmt:
            self.fmt = fmt

    def serialize(self, value):
        return struct.pack(self.fmt, value)

    def deserialize(self, value):
        length = struct.calcsize(self.fmt)
        return length, struct.unpack_from(self.fmt, value)[0]


class BlobSerializer(BaseSerializer):
    # Reference: https://xrpl.org/serialization.html#length-prefixing
    def serialize(self, value):
        length = len(value)
        if length > 918744:
            raise ValueError('Payload too long, should be <= 918744')

        prefix = []
        if length <= 192:
            prefix = length,
        elif length <= 12480:
            length -= 193
            prefix = (length >> 8) + 193, length & 255
        elif length <= 918744:
            length -= 12481
            prefix = 241 + (length >> 16), (length >> 8) & 255, length & 255
        return b''.join((bytes(prefix), value))

    def deserialize(self, value):
        byte0, byte1, byte2 = value[:3]
        if byte0 <= 192:
            offset = 1
            length = byte0
        elif byte0 <= 240:
            offset = 2
            length = 193 + ((byte0 - 193) * 256) + byte1
        else:
            offset = 3
            length = 12481 + ((byte0 - 241) * 65536) + (byte1 * 256) + byte2
        return length + offset, value[offset:offset + length]


class AccountIDSerializer(BlobSerializer):
    def serialize(self, value):
        value = decode_address(value)
        return super().serialize(value)

    def deserialize(self, value):
        length, value = super().deserialize(value)
        return length, encode_address(value)


class CurrencySerializer(BaseSerializer):
    def deserialize(self, value):
        # Currency code is formatted in such a way, that first 12 bytes
        # are reserved and last 5 bytes are also reserved
        return 20, value[12:15].decode()

    def serialize(self, value):
        return value[:3].encode().rjust(15, b'\x00').ljust(20, b'\x00')


class AmountSerializer(BaseSerializer):
    MIN_MANTISSA = 10**15
    MAX_MANTISSA = 10**16 - 1
    MIN_EXP = -96
    MAX_EXP = 80

    def scale_to_xrp_amount(self, value):
        amount = (value * (D(10) ** 15)).normalize()
        diff = amount.adjusted() - 15
        exp = -15 + diff
        mantissa = abs(int(amount / D(10) ** diff))
        if exp < self.MIN_EXP or mantissa < self.MIN_MANTISSA:
            return (False, 0, 0)
        if exp > self.MAX_EXP or mantissa > self.MAX_MANTISSA:
            raise ValueError('Amount out of range')
        return amount.is_signed(), mantissa, exp

    def serialize(self, value):
        # XRP is passed as int, Issued Currency as dict
        if isinstance(value, int):
            amount = value
            if amount >= 0:
                amount |= 0x4000000000000000
            else:
                amount = -amount
            return BasicTypeSerializer('>Q').serialize(amount)
        elif isinstance(value, dict):
            # Issued Currency
            amount = D(value.get('value'))
            currency = value.get('code')
            issuer = value.get('issuer')

            serialized_amount = 0x8000000000000000
            sign, mantissa, exp = self.scale_to_xrp_amount(amount)

            # When mantissa == 0, it means we're rounding to 0
            if mantissa != 0:
                # set "Is positive" bit
                if sign == 0:
                    serialized_amount |= 0x4000000000000000

                # next 8 bits are exponent
                serialized_amount |= ((exp + 97) << 54)
                # last 54 bits are mantissa
                serialized_amount |= mantissa

            return b''.join((
                BasicTypeSerializer('>Q').serialize(serialized_amount),
                CurrencySerializer().serialize(currency),
                decode_address(issuer)
            ))
        raise ValueError('Unsupported type, expected dict or int')

    def deserialize(self, value):
        # 1st bit indicates if this is an Issued Currency
        # 2nd bit indicates if it's a positive value
        is_issued_currency = value[0] & 0x80
        is_positive = value[0] & 0x40
        if is_issued_currency:
            exponent = ((value[0] & 0x3F) << 2) + ((value[1] & 0xff) >> 6) - 97
            length, amount = BasicTypeSerializer('>Q').deserialize(value)
            amount = (amount & 0x003FFFFFFFFFFFFF) * 10**exponent

            # Currency code is formatted in such a way, that first 12 bytes
            # are reserved and last 5 bytes are also reserved
            _, currency_code = CurrencySerializer().deserialize(value[8:28])
            return 48, {
                'issuer': encode_address(value[28:48]),
                'value': amount if is_positive else -amount,
                'code': currency_code
            }

        length, amount = BasicTypeSerializer('>Q').deserialize(value)
        amount &= 0x3FFFFFFFFFFFFFFF
        return length, amount if is_positive else -amount


class ArraySerializer(BaseSerializer):
    def serialize(self, value):
        results = []
        for obj in value:
            results.append(serialize(obj))
            results.append(serialize({'ObjectEndMarker': {}}))
        return b''.join((*results, b'\xf1'))

    def deserialize(self, value):
        results = []
        cursor = 0
        while True:
            if value[cursor] == 0xf1:
                cursor += 1
                break
            length, field = lookup_field(value[cursor:])
            cursor += length
            values = {}
            length, values[field.name] = decode(field.name, value[cursor:])
            cursor += length
            results.append(values)
        return cursor, results


class HashSerializer(BaseSerializer):
    def __init__(self, length):
        self.length = length

    def serialize(self, value):
        assert len(value) == self.length
        return value

    def deserialize(self, value):
        return self.length, value[:self.length]


class PathSetSerializer(BaseSerializer):
    def serialize(self, value):
        ccy_serializer = CurrencySerializer()
        results = []
        for path in value:
            path_data = []
            for step in path:
                type_byte = 0
                data = []
                if "account" in step.keys():
                    type_byte |= 0x01
                    data.append(decode_address(step['account']))
                if "currency" in step.keys():
                    type_byte |= 0x10
                    data.append(ccy_serializer.serialize(step['currency']))
                if "issuer" in step.keys():
                    type_byte |= 0x20
                    data.append(decode_address(step['issuer']))
                path_data.append(b''.join((
                    BasicTypeSerializer('>B').serialize(type_byte),
                    *data
                )))
            results.append(b''.join(path_data))
        return b''.join((b'\xFF'.join(results), b'\x00'))

    def deserialize(self, value):
        results = []
        cursor = 0
        while True:
            if value[cursor] == 0x00:
                cursor += 1
                break
            path = []
            while cursor < len(value) - 1:
                if value[cursor] == 0xFF:
                    cursor += 1
                    break
                step = {}
                step_type = value[cursor]
                cursor += 1
                if step_type & 0x01:
                    step['account'] = encode_address(value[cursor:cursor + 20])
                    cursor += 20
                if step_type & 0x10:
                    length, currency_code = CurrencySerializer().deserialize(
                        value[cursor:]
                    )
                    step['currency'] = currency_code
                    cursor += length
                if step_type & 0x20:
                    step['issuer'] = encode_address(value[cursor:cursor + 20])
                    cursor += 20
                path.append(step)
            results.append(path)
        return cursor, results


class ObjectSerializer(BaseSerializer):
    def serialize(self, value):
        """
        To serialize an object to Ripple format, we need to follow these steps:
        1. Convert each field data to binary format
        2. Sort fields in "canonical order"
        3. Prefix each field with a field ID.
        4. Concatenate fields (with prefixes) in their sorted order
        """
        serialized = {
            k: encode(k, v)
            for k, v in value.items()
        }
        canonical_order = sorted(
            serialized.keys(),
            key=lambda k: (
                RIPPLE_FIELDS[k].type_, RIPPLE_FIELDS[k].nth
            )
        )
        return b''.join(serialized[k] for k in canonical_order)

    def deserialize(self, value):
        cursor = 0
        values = {}
        while cursor < len(value):
            length, field = lookup_field(value[cursor:])
            cursor += length
            if field.name == 'ObjectEndMarker':
                break
            length, values[field.name] = decode(field.name, value[cursor:])
            cursor += length
        return cursor, values


TYPE_MAPPING = {
    RippleType.UInt8: BasicTypeSerializer('>B'),
    RippleType.UInt16: BasicTypeSerializer('>H'),
    RippleType.UInt32: BasicTypeSerializer('>I'),
    RippleType.UInt64: BasicTypeSerializer('>Q'),
    RippleType.Blob: BlobSerializer(),
    RippleType.AccountID: AccountIDSerializer(),
    RippleType.Amount: AmountSerializer(),
    RippleType.STArray: ArraySerializer(),
    RippleType.Hash128: HashSerializer(16),
    RippleType.Hash160: HashSerializer(20),
    RippleType.Hash256: HashSerializer(32),
    RippleType.PathSet: PathSetSerializer(),
    RippleType.STObject: ObjectSerializer()
}


# TODO:
# check if we need to support Metadata, Validation, LedgerEntry, Transaction
# and Vector256 types


def encode(key, value):
    field = RIPPLE_FIELDS[key]
    field_id = b''.join(
        BasicTypeSerializer('>B').serialize(byte) for byte in field.field_id
    )

    if field.type_ in TYPE_MAPPING:
        return b''.join((
            field_id, TYPE_MAPPING.get(field.type_).serialize(value)
        ))

    # if type is not supported, raise an Exception
    raise RippleSerializerUnsupportedTypeException(field.type_)


def decode(key, binary):
    field = RIPPLE_FIELDS[key]
    if field.type_ in TYPE_MAPPING:
        return TYPE_MAPPING.get(field.type_).deserialize(binary)

    # if type is not supported, raise an Exception
    raise RippleSerializerUnsupportedTypeException(field.type_)


def lookup_field(binary):
    # Reference: https://xrpl.org/serialization.html#field-ids
    high = binary[0] >> 4
    low = binary[0] % 16

    if high:
        type_code = high
        field_code = low if low else binary[1]
        length = 1 if low else 2
    else:
        type_code = binary[1]
        field_code = low if low else binary[2]
        length = 2 if low else 3

    return length, RIPPLE_FIELDS_LOOKUP[type_code].get(field_code)


def serialize(obj):
    return ObjectSerializer().serialize(obj)


def deserialize(binary):
    if isinstance(binary, str):
        binary = unhexlify(binary)
    _, obj = ObjectSerializer().deserialize(binary)
    return obj
