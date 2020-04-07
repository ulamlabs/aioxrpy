import base58
import binascii

import ecdsa
import hashlib
import secrets

from aioxrpy.address import encode_address
from aioxrpy.hash import first_half_of_sha512, hash_transaction


def signing_key_from_seed(seed):
    """
    This derives your master key the given seed.

    Reference:
    https://ripple.com/wiki/Account_Family#Root_Key_.28GenerateRootDeterministicKey.29
    """
    # Ripple seeds are base58 strings prefixed with "s" letter
    assert seed[0] == 's'
    seed = base58.b58decode_check(seed, alphabet=base58.RIPPLE_ALPHABET)[1:]

    seq = 0
    while True:
        private_gen = int.from_bytes(
            first_half_of_sha512(
                b''.join([seed, seq.to_bytes(4, byteorder='big')])
            ),
            byteorder='big'
        )
        seq += 1
        if ecdsa.SECP256k1.order >= private_gen:
            break

    public_key = ecdsa.VerifyingKey.from_public_point(
        ecdsa.SECP256k1.generator * private_gen, curve=ecdsa.SECP256k1
    )

    # Now that we have the private and public generators, we apparently
    # have to calculate a secret from them that can be used as a ECDSA
    # signing key.
    secret = i = 0
    public_gen_compressed = public_key.to_string(encoding='compressed')
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
        if ecdsa.SECP256k1.order >= secret:
            break
    secret = (secret + private_gen) % ecdsa.SECP256k1.order

    # The ECDSA signing key object will, given this secret, then expose
    # the actual private and public key we are supposed to work with.
    key = ecdsa.SigningKey.from_secret_exponent(secret, ecdsa.SECP256k1)
    # Attach the generators as supplemental data
    key.private_gen = private_gen
    return key


class RippleKey:
    """
    RippleKey instance.

    Depends on which kwargs are given, this works in a different way:
    - No kwargs - generates a new private key
    - Only private_key - public key is being derived from private key
    - Only public_key - RippleKey instance has no private key
    """
    def __init__(self, *, private_key: str = None, public_key: str = None):
        assert not (private_key and public_key), 'Pass only 1 key'
        if public_key:
            self._vk = ecdsa.VerifyingKey.from_string(
                public_key, curve=ecdsa.SECP256k1
            )
            return

        if private_key:
            try:
                self._sk = ecdsa.SigningKey.from_string(
                    binascii.unhexlify(private_key), curve=ecdsa.SECP256k1
                )
            except (AssertionError, binascii.Error):
                self._sk = signing_key_from_seed(private_key)
        else:
            entropy = ecdsa.util.PRNG(secrets.randbits(512))
            self._sk = ecdsa.SigningKey.generate(
                entropy=entropy, curve=ecdsa.SECP256k1
            )

        self._vk = self._sk.get_verifying_key()

    def to_public(self):
        return self._vk.to_string(encoding='compressed')

    def to_account(self):
        pubkey = self.to_public()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(hashlib.sha256(pubkey).digest())
        return encode_address(ripemd160.digest())

    def sign_tx(self, tx, multi_signer=None, **kwargs):
        return self.sign(
            hash_transaction(tx, multi_signer=multi_signer), **kwargs
        )

    def verify_tx(self, tx, signature, multi_signer=None):
        return self.verify(
            hash_transaction(tx, multi_signer=multi_signer), signature
        )

    def sign(self, data, **kwargs):
        """
        TODO: try to make use of self._sk.sign_digest() instead
        """
        data = int.from_bytes(data, byteorder='big')
        r, s = self._sk.sign_number(data, **kwargs)

        # make s canonical
        N = ecdsa.curves.SECP256k1.order
        if not N / 2 >= s:
            s = N - s

        return ecdsa.util.sigencode_der(r, s, None)

    def verify(self, data, signature, **kwargs):
        return self._vk.verify_digest(
            signature,
            data,
            sigdecode=ecdsa.util.sigdecode_der,
            **kwargs
        )
