import base58
from typing import Callable, Dict, Optional, Union

from ecdsa.curves import SECP256k1
from ecdsa.keys import SigningKey, VerifyingKey
from ecdsa.util import sigencode_der, sigdecode_der, PRNG
import hashlib
import secrets

from aioxrpy.address import decode_address, encode_address
from aioxrpy.definitions import RippleTransactionHashPrefix
from aioxrpy.hash import first_half_of_sha512, hash_transaction


def make_canonical(r, s, order):
    """Makes ecdsa signature canonical"""
    N = SECP256k1.order
    if not N / 2 >= s:
        s = N - s
    return r, s, order


def signing_key_from_seed(encoded_seed: str) -> SigningKey:
    """
    Derives SigningKey from master seed.

    Reference:
    https://ripple.com/wiki/Account_Family#Root_Key_.28GenerateRootDeterministicKey.29
    """
    # Ripple seeds are base58-encoded and prefixed with letter "s"
    assert encoded_seed[0] == 's'
    seed = base58.b58decode_check(
        encoded_seed, alphabet=base58.RIPPLE_ALPHABET
    )[1:]

    seq = 0
    while True:
        private_gen = int.from_bytes(
            first_half_of_sha512(seed, seq.to_bytes(4, byteorder='big')),
            byteorder='big'
        )
        seq += 1
        if SECP256k1.order >= private_gen:
            break

    public_key = VerifyingKey.from_public_point(
        SECP256k1.generator * private_gen, curve=SECP256k1
    )

    # Now that we have the private and public generators, we apparently
    # have to calculate a secret from them that can be used as a ECDSA
    # signing key.
    secret = i = 0
    public_gen_compressed = public_key.to_string(encoding='compressed')
    while True:
        secret = int.from_bytes(
            first_half_of_sha512(
                public_gen_compressed, bytes(4), i.to_bytes(4, byteorder='big')
            ),
            byteorder='big'
        )
        i += 1
        if SECP256k1.order >= secret:
            break

    secret = (secret + private_gen) % SECP256k1.order
    return SigningKey.from_secret_exponent(secret, curve=SECP256k1)


class RippleKey:
    """
    RippleKey instance

    :param private_key: private key or master seed,
    :param public_key: public key

    If no arguments are passed, new key will be generated.
    """

    def __init__(
        self,
        *,
        private_key: Optional[Union[str, bytes]] = None,
        public_key: Optional[bytes] = None
    ):
        assert not (private_key and public_key), 'Pass only one key'
        if public_key:
            self._sk = None
            self._vk = VerifyingKey.from_string(public_key, curve=SECP256k1)
            return

        if private_key:
            if isinstance(private_key, str):
                self._sk = signing_key_from_seed(private_key)
            else:
                self._sk = SigningKey.from_string(private_key, curve=SECP256k1)
        else:
            entropy = PRNG(secrets.randbits(512))
            self._sk = SigningKey.generate(
                entropy=entropy, curve=SECP256k1
            )

        self._vk = self._sk.get_verifying_key()

    def to_public(self) -> bytes:
        """
        Returns public key encoded in compressed format.
        """
        return self._vk.to_string(encoding='compressed')

    def to_account(self) -> str:
        """
        Returns base58-encoded RIPEMD-160 hash of SHA256 hash of public key,
        which is used as an account name on Ripple ledger.

        For example: ``rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh``
        """
        pubkey = self.to_public()
        ripemd160 = hashlib.new('ripemd160')
        ripemd160.update(hashlib.sha256(pubkey).digest())
        return encode_address(ripemd160.digest())

    def _tx_prefix(self, multi_sign: bool) -> bytes:
        return (
            RippleTransactionHashPrefix.HASH_TX_SIGN
            if not multi_sign
            else RippleTransactionHashPrefix.HASH_TX_SIGN_MULTI
        )

    def _tx_suffix(self, multi_sign: bool) -> bytes:
        return b'' if not multi_sign else decode_address(self.to_account())

    def sign_tx(self, tx: Dict, *, multi_sign: bool = False, **kwargs) -> str:
        tx_hash = hash_transaction(
            self._tx_prefix(multi_sign), tx, self._tx_suffix(multi_sign)
        )
        return self.sign(tx_hash, **kwargs)

    def verify_tx(
        self, tx: Dict, signature: str, *, multi_sign: bool = False, **kwargs
    ) -> bool:
        tx_hash = hash_transaction(
            self._tx_prefix(multi_sign), tx, self._tx_suffix(multi_sign)
        )
        return self.verify(tx_hash, signature, **kwargs)

    def sign(
        self, data: bytes, sigencode: Callable = sigencode_der, **kwargs
    ) -> str:
        """
        Signs the provided data and returns a canonical signature
        """
        assert self._sk is not None, "Can't sign with a public key"
        return sigencode(*self._sk.sign_digest(
            data, sigencode=make_canonical, **kwargs
        ))

    def verify(
        self,
        data: bytes,
        signature: str,
        *,
        sigdecode: Callable = sigdecode_der,
        **kwargs
    ) -> bool:
        return self._vk.verify_digest(
            signature, data, sigdecode=sigdecode, **kwargs
        )
