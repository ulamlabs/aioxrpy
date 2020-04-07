import binascii

from aioxrpy import decimals, serializer
from aioxrpy.definitions import RippleTransactionType
from aioxrpy.rpc import RippleJsonRpc
from aioxrpy.sign import (
    sign_transaction, root_key_from_hex, root_key_from_seed, parse_seed,
    verify_transaction
)


def _get_private_key(key):
    """We store private keys for wallets in two formats:
    - master seed - a base58 encoded string that starts with 's' and is
                    used to derive a real private key
    - private key - hex encoded SECP256k1 signing key, usually we'll get
                    these when deriving keys from XPRIV
    This method tries to parse it and returns a SigningKey object
    """
    try:
        # This is more likely to fail, so let's try this first
        return root_key_from_hex(key)
    except (AssertionError, binascii.Error):
        seed = parse_seed(key)
        return root_key_from_seed(seed)


async def test_tx_flow():
    """
    Tests transaction serialization, signing and submitting flow
    """
    rpc = RippleJsonRpc('http://localhost:5005')

    # Master account from genesis ledger
    # https://xrpl.org/start-a-new-genesis-ledger-in-stand-alone-mode.html
    from_account = 'rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh'
    master_seed = 'snoPBrXtMeMyMHUVTgbuqAfg1SUTb'
    private_key = _get_private_key(master_seed)

    to_account = 'rsjBEELRmVFWHfs6cE3xPcus63tNNpZvkT'

    fee_response = await rpc.fee()
    fee = fee_response['drops']['minimum_fee']

    account_info = await rpc.account_info(
        from_account, ledger_index='current'
    )
    sequence = account_info['account_data']['Sequence']

    reserve = await rpc.get_reserve()

    tx = {
        'Account': from_account,
        'Sequence': sequence,
        'TransactionType': RippleTransactionType.Payment,
        'Amount': decimals.xrp_to_drops(reserve.base),
        'Destination': to_account,
        'Fee': int(fee)  # as drops
    }

    # sign and serialize transaction
    sign_transaction(tx, private_key)
    tx_blob = binascii.hexlify(serializer.serialize(tx)).decode()

    # deserialize and verify signatures
    deserialized_tx = serializer.deserialize(tx_blob)
    assert deserialized_tx == tx

    public_key = private_key.get_verifying_key()
    assert verify_transaction(deserialized_tx, public_key)

    # post TX blob to rippled JSONRPC
    result = await rpc.submit(tx_blob)
    assert result['engine_result'] == 'tesSUCCESS'
