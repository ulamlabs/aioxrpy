from ecdsa.util import sigencode_der
from aioxrpy.sign import (
    parse_seed, root_key_from_seed, get_ripple_from_pubkey,
    ecc_point_to_bytes_compressed, get_ripple_from_secret,
    create_signing_hash, ecdsa_make_canonical, ecdsa_sign,
    ecdsa_verify
)
from aioxrpy.definitions import RippleTransactionType


def test_parse_seed():
    # To get the reference value in ripple-lib:
    #    Seed.from_json(...)._value.toString()
    parsed = parse_seed('ssq55ueDob4yV3kPVnNQLHB6icwpC')
    assert parsed == b'R2\x90\xe66\xd6\xcdAE\xf3\xf0?\x85IWz'


def test_wiki_test_vector():
    # https://ripple.com/wiki/Account_Family#Test_Vectors
    seed = parse_seed('shHM53KPZ87Gwdqarm1bAmPeXg8Tn')
    assert seed == b'q\xed\x06AU\xff\xad\xfa8x,^\x01X\xcb&'

    key = root_key_from_seed(seed)
    assert key.private_gen == (
        56531419669858502233010723520717330944031766521662186235427530210896940609752  # noqa
    )

    assert get_ripple_from_pubkey(
        ecc_point_to_bytes_compressed(key.privkey.public_key.point)
    ) == 'rhcfR9Cg98qCxHpCcPBmMonbDBXo84wyTn'


def test_key_derivation():
    key = root_key_from_seed(parse_seed('ssq55ueDob4yV3kPVnNQLHB6icwpC'))
    # This ensures the key was properly initialized
    expected = (
        '0x902981cd5e0c862c53dc4854b6da4cc04179a2a524912d79800ac4c95435564d'
    )
    assert hex(key.privkey.secret_multiplier) == expected


def test_ripple_from_secret():
    assert get_ripple_from_secret('shHM53KPZ87Gwdqarm1bAmPeXg8Tn') == (
        'rhcfR9Cg98qCxHpCcPBmMonbDBXo84wyTn'
    )


def test_signing_hash():
    assert create_signing_hash({
        "TransactionType": RippleTransactionType.Payment
    }) == (
        b'\x90<\x92fA\t[9*\x12=L\xcd\x19\xe0`\xdd\x8a`<\x91\xdd\xff%J\xc9\xad;'
        b'\x98l\x10\xcf'
    )


def test_der_encoding():
    # This simply verifies that the DER encoder from the ECDSA lib
    # we're using does the right thing and matches the output of the
    # DER encoder of ripple-lib.
    assert sigencode_der(
        115581891344481397258725970875952747678118488142456103749636233920875606682075,  # noqa
        92390792920050736459282310733499227334693505881527196271213621127186919137975,  # noqa
        None
    ) == (
        b'0F\x02!\x00\xff\x89\x08>\xd4\x92;3y8\x18&3\x9caJ\xc1\xcby\xbf6\xb1'
        b'\x8c4\xd5\xe9w\x84\xc5\xa5\xa9\xdb\x02!\x00\xccCU\xed\xa8\xcey\xc6'
        b')\xfbS\xb0\xd1\x9a\xbc\x1bT=\x9f\x17F&\xcf3\xb8\xa2bT\xc6;"\xb7'
    )


def test_canonical_signature():
    # From https://github.com/ripple/ripple-lib/blob/9d6ccdcab1fc237dbcfae41fc9e0ca1d2b7565ca/test/sjcl-ecdsa-canonical-test.js  # noqa
    def parse_hex_sig(hexstring):
        length = len(hexstring)
        r = int(hexstring[:length//2], 16)
        s = int(hexstring[length//2:], 16)
        return r, s

    # Test a signature that will be canonicalized
    input = (
        "27ce1b914045ba7e8c11a2f2882cb6e07a19d4017513f12e3e363d71dc3fff0fb"
        "0a0747ecc7b4ca46e45b3b32b6b2a066aa0249c027ef11e5bce93dab756549c"
    )
    r, s = ecdsa_make_canonical(*parse_hex_sig(input))
    assert (r, s) == parse_hex_sig(
        '27ce1b914045ba7e8c11a2f2882cb6e07a19d4017513f12e3e363d71dc3fff0f'
        '4f5f8b813384b35b91ba4c4cd494d5f8500eb84aacc9af1d6403cab218dfeca5'
    )

    # Test a signature that is already fully-canonical
    input = (
        "5c32bc2b4d34e27af9fb66eeea0f47f6afb3d433658af0f649ebae7b872471ab"
        "7d23860688aaf9d8131f84cfffa6c56bf9c32fd8b315b2ef9d6bcb243f7a686c"
    )
    r, s = ecdsa_make_canonical(*parse_hex_sig(input))
    assert (r, s) == parse_hex_sig(input)


def test_sign():
    # Verify a correct signature is created (uses a fixed k value):
    key = root_key_from_seed(parse_seed('ssq55ueDob4yV3kPVnNQLHB6icwpC'))
    public_key = key.get_verifying_key()
    signature = ecdsa_sign(key, b'\xff\x00\xee\xcc', k=3)
    assert signature == (
        b'0E\x02!\x00\xf90\x8a\x01\x92X\xc3\x10I4O\x85\xf8\x9dR)\xb51\xc8E'
        b'\x83o\x99\xb0\x86\x01\xf1\x13\xbc\xe06\xf9\x02 _mX\xbea\x82\xb9'
        b'\xa1\xe0O\xce\xc3ouf\x8d\xea\xfa\xd2\xe43kHw\x0e\xe5\xc5Y\xd3Q'
        b'\x83\x01'
    )
    assert ecdsa_verify(public_key, b'\xff\x00\xee\xcc', signature)
