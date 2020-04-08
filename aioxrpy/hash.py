import hashlib
from typing import Dict

from aioxrpy import serializer


def first_half_of_sha512(*data: bytes) -> bytes:
    """Returns first 32 bytes of SHA512 hash"""
    return hashlib.sha512(b''.join(data)).digest()[:32]  # 256 / 8


def hash_transaction(prefix: bytes, tx: Dict, suffix: bytes) -> bytes:
    """
    Serializes transaction object and returns first half of SHA512 hash
    """
    return first_half_of_sha512(prefix, serializer.serialize(tx), suffix)
