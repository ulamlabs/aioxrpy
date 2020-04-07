import binascii
from aioxrpy.keys import RippleKey, signing_key_from_seed


def test_key_derivation():
    key = signing_key_from_seed('ssq55ueDob4yV3kPVnNQLHB6icwpC')
    assert hex(key.privkey.secret_multiplier) == (
        '0x902981cd5e0c862c53dc4854b6da4cc04179a2a524912d79800ac4c95435564d'
    )


def test_xrp_key_from_seed():
    key = RippleKey(private_key='shHM53KPZ87Gwdqarm1bAmPeXg8Tn')
    assert key._sk.private_gen == (
        56531419669858502233010723520717330944031766521662186235427530210896940609752  # noqa
    )
    assert key.to_account() == 'rhcfR9Cg98qCxHpCcPBmMonbDBXo84wyTn'


def test_xrp_key_from_hex():
    hex_key = (
        '42aa52b7da6fc94b8ee8946aeccafb6a03b1f62de2095834e3dcf26d55e0d458'
    )
    key = RippleKey(private_key=hex_key)
    assert binascii.hexlify(key._sk.to_string()).decode() == hex_key


def test_xrp_key_creating():
    key1 = RippleKey()
    key2 = RippleKey()
    assert key1._sk.to_string() != key2._sk.to_string()


def test_xrp_key_to_public():
    key = RippleKey(private_key='shHM53KPZ87Gwdqarm1bAmPeXg8Tn')
    assert key.to_public() == (
        b'\x03\xfa%\xb6\x8d\xa6\xffh2\xe4F/\xdf\xb9\xa2\xaa\xa5\x88\x88\xc0'
        b'\xed\x17(_\xfe\x92\xe4F^\x0cnx*'
    )


def test_xrp_key_to_account():
    key = RippleKey(private_key='shHM53KPZ87Gwdqarm1bAmPeXg8Tn')
    assert key.to_account() == 'rhcfR9Cg98qCxHpCcPBmMonbDBXo84wyTn'


def test_xrp_key_signature():
    key = RippleKey(private_key='ssq55ueDob4yV3kPVnNQLHB6icwpC')
    data = {
        'Account': key.to_account()
    }

    # sign data with fixed k value for deterministic result
    signature = key.sign_tx(data, k=3)
    assert signature == (
        b'0E\x02!\x00\xf90\x8a\x01\x92X\xc3\x10I4O\x85\xf8\x9dR)\xb51\xc8E'
        b'\x83o\x99\xb0\x86\x01\xf1\x13\xbc\xe06\xf9\x02 k\x1d*S_\xf1`\x17'
        b'\xae\twl\x94/\x82\x03\x07E\xaf\xa0\xc1\x8e\xed\xfbv\xf6\xf6\xc8'
        b'\xba\x8aW\xdb'
    )
    assert key.verify_tx(data, signature)
