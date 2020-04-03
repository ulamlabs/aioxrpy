"""
Ripple definitions.json converted to Python object
"""
from collections import defaultdict
from dataclasses import dataclass
from enum import IntEnum
import json
import os
from typing import Dict


DEFINITIONS_PATH = os.path.join(os.path.dirname(__file__), 'definitions.json')


with open(DEFINITIONS_PATH) as dfile:
    definitions = json.load(dfile)


def _init_enum(name: str, key: str):
    values = definitions.get(key, {})
    return IntEnum(name, values)


RippleLedgerEntryType = _init_enum(
    'RippleLedgerEntryType', 'LEDGER_ENTRY_TYPES'
)
RippleTransactionResult = _init_enum(
    'RippleTransactionResult', 'TRANSACTION_RESULTS'
)
RippleTransactionType = _init_enum(
    'RippleTransactionType', 'TRANSACTION_TYPES'
)


class RippleType(IntEnum):
    Validation = 10003
    Done = -1
    Hash128 = 4
    Blob = 7
    AccountID = 8
    Amount = 6
    Hash256 = 5
    UInt8 = 16
    Vector256 = 19
    STObject = 14
    Unknown = -2
    Transaction = 10001
    Hash160 = 17
    PathSet = 18
    LedgerEntry = 10002
    UInt16 = 1
    NotPresent = 0
    UInt64 = 3
    UInt32 = 2
    STArray = 15


@dataclass
class RippleField:
    name: str
    is_serialized: bool
    is_signing_field: bool
    is_vl_encoded: bool
    nth: int
    type_: RippleType

    @property
    def field_id(self):
        type_code = self.type_
        field_code = self.nth

        # Codes must be nonzero and fit in 1 byte
        assert 0 < field_code <= 255
        assert 0 < type_code <= 255

        if type_code < 16 and field_code < 16:
            # high 4 bits is the type_code
            # low 4 bits is the field code
            combined_code = (type_code << 4) | field_code
            return combined_code,
        elif type_code >= 16 and field_code < 16:
            # first 4 bits are zeroes
            # next 4 bits is field code
            # next byte is type code
            byte1 = field_code
            byte2 = type_code
            return byte1, byte2,
        elif type_code < 16 and field_code >= 16:
            # first 4 bits is type code
            # next 4 bits are zeroes
            # next byte is field code
            byte1 = type_code << 4
            byte2 = field_code
            return byte1, byte2,
        else:
            # both are >= 16
            # first byte is all zeroes
            # second byte is type
            # third byte is field code
            byte2 = type_code
            byte3 = field_code
            return 0, byte2, byte3,

    @classmethod
    def from_definition(cls, name, definition):
        return cls(
            name=name,
            is_serialized=definition['isSerialized'],
            is_signing_field=definition['isSigningField'],
            is_vl_encoded=definition['isVLEncoded'],
            nth=definition['nth'],
            type_=RippleType[definition['type']]
        )


RIPPLE_FIELDS = {}
RIPPLE_FIELDS_LOOKUP = defaultdict(dict)  # type: Dict[str, Dict]

for k, v in definitions['FIELDS']:
    field = RippleField.from_definition(k, v)
    RIPPLE_FIELDS[k] = field
    RIPPLE_FIELDS_LOOKUP[field.type_][field.nth] = field
