import hashlib

from aioxrpy import address, serializer
from aioxrpy.definitions import RippleTransactionHashPrefix


def first_half_of_sha512(*binary):
    """As per spec, this is the hashing function used."""
    h = hashlib.sha512()
    for part in binary:
        h.update(part)
    return h.digest()[:32]  # 256 / 8


def hash_transaction(transaction, multi_signer=None):
    prefix = (
        RippleTransactionHashPrefix.HASH_TX_SIGN_MULTI
        if multi_signer else RippleTransactionHashPrefix.HASH_TX_SIGN
    )
    buff = [prefix, serializer.serialize(transaction)]
    if multi_signer:
        buff.append(address.decode_address(multi_signer))
    return first_half_of_sha512(b''.join(buff))
