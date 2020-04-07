import binascii

import pytest

from aioxrpy import decimals, serializer
from aioxrpy.definitions import RippleTransactionType, RippleTransactionFlags
from aioxrpy.keys import RippleKey
from aioxrpy.rpc import RippleJsonRpc


@pytest.fixture
def master():
    # Master account from genesis ledger
    # https://xrpl.org/start-a-new-genesis-ledger-in-stand-alone-mode.html
    return RippleKey(private_key='snoPBrXtMeMyMHUVTgbuqAfg1SUTb')


async def test_tx_flow_single_sign(master):
    """
    Tests transaction serialization, signing and submitting flow
    """
    rpc = RippleJsonRpc('http://localhost:5005')
    fee = await rpc.fee()
    reserve = await rpc.get_reserve()

    destination = RippleKey()

    account_info = await rpc.account_info(
        master.to_account(), ledger_index='current'
    )

    tx = {
        'Account': master.to_account(),
        'Flags': RippleTransactionFlags.FullyCanonicalSig,
        'Sequence': account_info['account_data']['Sequence'],
        'TransactionType': RippleTransactionType.Payment,
        'Amount': decimals.xrp_to_drops(reserve.base),
        'Destination': destination.to_account(),
        'Fee': int(fee.minimum),  # as drops
        'SigningPubKey': master.to_public()
    }

    # sign and serialize transaction
    signature = master.sign_tx(tx)
    signed_tx = {
        **tx,
        'TxnSignature': signature
    }
    tx_blob = binascii.hexlify(serializer.serialize(signed_tx)).decode()

    # deserialize and verify signatures
    deserialized_tx = serializer.deserialize(tx_blob)
    public_key = RippleKey(public_key=deserialized_tx['SigningPubKey'])
    assert deserialized_tx == signed_tx
    assert public_key.verify_tx(tx, signature)

    # post TX blob to rippled JSONRPC
    result = await rpc.submit(tx_blob)
    assert result['engine_result'] == 'tesSUCCESS'


async def test_tx_flow_multi_sign(master):
    """
    Tests transaction serialization, signing and submitting flow with multiple
    keys
    """
    rpc = RippleJsonRpc('http://localhost:5005')
    reserve = await rpc.get_reserve()

    account = RippleKey()
    await rpc.sign_and_submit(
        {
            'Amount': decimals.xrp_to_drops((reserve.base * 2) + 100),
            'Flags': RippleTransactionFlags.FullyCanonicalSig,
            'TransactionType': RippleTransactionType.Payment,
            'Destination': account.to_account()
        },
        master
    )

    # Enable multi-signing
    account_key_1 = RippleKey()
    account_key_2 = RippleKey()
    await rpc.sign_and_submit(
        {
            "Flags": 0,
            "TransactionType": RippleTransactionType.SignerListSet,
            "SignerQuorum": 2,
            "SignerEntries": [
                {
                    "SignerEntry": {
                        "Account": account_key_1.to_account(),
                        "SignerWeight": 1
                    }
                },
                {
                    "SignerEntry": {
                        "Account": account_key_2.to_account(),
                        "SignerWeight": 1
                    }
                }
            ]
        },
        account
    )
    await rpc.ledger_accept()

    destination = RippleKey()
    result = await rpc.multisign_and_submit(
        {
            'Account': account.to_account(),
            'Flags': RippleTransactionFlags.FullyCanonicalSig,
            'TransactionType': RippleTransactionType.Payment,
            'Amount': decimals.xrp_to_drops(reserve.base),
            'Destination': destination.to_account()
        },
        [account_key_1, account_key_2]
    )
    assert result['engine_result'] == 'tesSUCCESS'
