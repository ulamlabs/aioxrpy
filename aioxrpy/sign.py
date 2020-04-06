"""
Shamelessly stolen from unmaintained ripple-python library

https://github.com/miracle2k/ripple-python/blob/master/ripple/sign.py
"""
from binascii import unhexlify
import hashlib

import base58
from ecdsa import curves, SigningKey
from ecdsa.util import sigencode_der, sigdecode_der

from aioxrpy.address import decode_address, encode_address
from aioxrpy.definitions import RippleTransactionFlags
from aioxrpy.serializer import serialize


def sign_transaction(transaction, private_key, flag_canonical=True):
    """High-level signing function.hexlify

    - Adds a signature (``TxnSignature``) field to the transaction object.
    - By default will set the ``FullyCanonicalSig`` flag to ``
    """
    if flag_canonical:
        transaction['Flags'] = (
            transaction.get('Flags', 0)
            | RippleTransactionFlags.FullyCanonicalSig
        )
    sig = signature_for_transaction(transaction, private_key)
    transaction['TxnSignature'] = sig
    return transaction


def verify_transaction(transaction, public_key, flag_canonical=True):
    signature = transaction.pop('TxnSignature')
    signing_hash = create_signing_hash(transaction)
    return ecdsa_verify(public_key, signing_hash, signature)


def signature_for_transaction(transaction, private_key, ismulti=False):
    """Calculate the fully-canonical signature of the transaction.

    Will set the ``SigningPubKey`` as appropriate before signing.

    ``transaction`` is a Python object. The result value is what you
    can insert into as ``TxSignature`` into the transaction structure
    you submit.
    """
    # Apparently the pub key is required to be there.
    if not ismulti:
        transaction['SigningPubKey'] = ecc_point_to_bytes_compressed(
            private_key.privkey.public_key.point
        )

    # Convert the transaction to a binary representation
    signerid = get_ripple_from_privkey(private_key)
    signing_hash = create_signing_hash(
        transaction, multi_signer=signerid if ismulti else None
    )

    # Create a hex-formatted signature.
    return ecdsa_sign(private_key, signing_hash)


def parse_seed(secret):
    """Your Ripple secret is a seed from which the true private key can
    be derived.

    The ``Seed.parse_json()`` method of ripple-lib supports different
    ways of specifying the seed, including a 32-byte hex value. We just
    support the regular base-encoded secret format given to you by the
    client when creating an account.
    """
    assert secret[0] == 's'
    return base58.b58decode_check(secret, alphabet=base58.RIPPLE_ALPHABET)[1:]


def root_key_from_hex(hex):
    return SigningKey.from_string(unhexlify(hex), curve=curves.SECP256k1)


def root_key_from_seed(seed):
    """This derives your master key the given seed.

    Implemented in ripple-lib as ``Seed.prototype.get_key``, and further
    is described here:
    https://ripple.com/wiki/Account_Family#Root_Key_.28GenerateRootDeterministicKey.29
    """
    seq = 0
    while True:
        seq_bytes = seq.to_bytes(4, byteorder='big')
        private_gen = int.from_bytes(
            first_half_of_sha512(b''.join([seed, seq_bytes])), byteorder='big'
        )
        seq += 1
        if curves.SECP256k1.order >= private_gen:
            break

    public_gen = curves.SECP256k1.generator * private_gen

    # Now that we have the private and public generators, we apparently
    # have to calculate a secret from them that can be used as a ECDSA
    # signing key.
    secret = i = 0
    public_gen_compressed = ecc_point_to_bytes_compressed(public_gen)
    while True:
        secret = int.from_bytes(
            first_half_of_sha512(
                b''.join([
                    public_gen_compressed,
                    bytes(4),
                    i.to_bytes(4, byteorder='big')
                ])
            ),
            byteorder='big'
        )
        i += 1
        if curves.SECP256k1.order >= secret:
            break
    secret = (secret + private_gen) % curves.SECP256k1.order

    # The ECDSA signing key object will, given this secret, then expose
    # the actual private and public key we are supposed to work with.
    key = SigningKey.from_secret_exponent(secret, curves.SECP256k1)
    # Attach the generators as supplemental data
    key.private_gen = private_gen
    key.public_gen = public_gen
    return key


def ecdsa_sign(key, signing_hash, **kw):
    """Sign the given data. The key is the secret returned by
    :func:`root_key_from_seed`.

    The data will be a binary coded transaction.
    """
    data = int.from_bytes(signing_hash, byteorder='big')
    r, s = key.sign_number(data, **kw)
    r, s = ecdsa_make_canonical(r, s)
    # Encode signature in DER format, as in
    # ``sjcl.ecc.ecdsa.secretKey.prototype.encodeDER``
    der_coded = sigencode_der(r, s, None)
    return der_coded


def ecdsa_verify(key, signing_hash, signature):
    return key.verify_digest(signature, signing_hash, sigdecode=sigdecode_der)


def ecdsa_make_canonical(r, s):
    """Make sure the ECDSA signature is the canonical one.

        https://github.com/ripple/ripple-lib/commit/9d6ccdcab1fc237dbcfae41fc9e0ca1d2b7565ca
        https://ripple.com/wiki/Transaction_Malleability
    """
    # For a canonical signature we want the lower of two possible values for s
    # 0 < s <= n/2
    N = curves.SECP256k1.order
    if not N / 2 >= s:
        s = N - s
    return r, s


def get_ripple_from_pubkey(pubkey):
    """Given a public key, determine the Ripple address.
    """
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(hashlib.sha256(pubkey).digest())
    return encode_address(ripemd160.digest())


def get_ripple_from_privkey(key):
    pubkey = ecc_point_to_bytes_compressed(key.privkey.public_key.point)
    return get_ripple_from_pubkey(pubkey)


def get_ripple_from_secret(seed):
    """Another helper. Returns the first ripple address from the secret."""
    key = root_key_from_seed(parse_seed(seed))
    return get_ripple_from_privkey(key)


# From ripple-lib:hashprefixes.js
HASH_TX_ID = 0x54584E00  # 'TXN'
HASH_TX_SIGN = 0x53545800  # 'STX'
HASH_TX_SIGN_MULTI = 0x534D5400  # 'SMT'


def create_signing_hash(transaction, multi_signer=None):
    """This is the actual value to be signed.

    It consists of a prefix and the binary representation of the
    transaction.
    """
    prefix = HASH_TX_SIGN_MULTI if multi_signer else HASH_TX_SIGN
    return hash_transaction(transaction, prefix, multi_signer)


def hash_transaction(transaction, prefix, multi_signer=None):
    """Create a hash of the transaction and the prefix.
    """
    buff = prefix.to_bytes(4, byteorder='big') + serialize(transaction)
    if multi_signer:
        buff += decode_address(multi_signer)
    binary = first_half_of_sha512(buff)
    return binary


def first_half_of_sha512(*bytes):
    """As per spec, this is the hashing function used."""
    hash = hashlib.sha512()
    for part in bytes:
        hash.update(part)
    return hash.digest()[:256//8]


def ecc_point_to_bytes_compressed(point):
    """
    In ripple-lib, implemented as a prototype extension
    ``sjcl.ecc.point.prototype.toBytesCompressed`` in ``sjcl-custom``.

    Also implemented as ``KeyPair.prototype._pub_bits``, though in
    that case it explicitly first pads the point to the bit length of
    the curve prime order value.
    """

    header = b'\x02' if point.y() % 2 == 0 else b'\x03'
    x = point.x()
    encoded = x.to_bytes(
        curves.SECP256k1.order.bit_length() // 8, byteorder='big'
    )
    return b"".join([header, encoded])
