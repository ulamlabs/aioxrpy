import base58


def decode_address(address):
    decoded = base58.b58decode_check(address, alphabet=base58.RIPPLE_ALPHABET)
    if decoded[0] == 0 and len(decoded) == 21:  # is an address
        return decoded[1:]
    else:
        raise ValueError("Not an AccountID!")


def encode_address(value):
    return base58.b58encode_check(
        b''.join((b'\x00', value)), alphabet=base58.RIPPLE_ALPHABET
    ).decode()
