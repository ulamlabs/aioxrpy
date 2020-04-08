Introduction
============

Ripple blockchain library for Python.

Features
--------

1. Async JSON-RPC client.
2. Signing and verifying transactions using private and public keys.
3. Support for signing transactions with multiple keys.
4. Serializer and deserializer for Ripple objects.

Getting Started
---------------

This guide step-by-step explains how to use aioxrpy library to submit your
first transaction. Complete example is available at the end of this chapter. 
Before we begin, please make sure that you have a rippled node running in
`stand-alone mode <https://xrpl.org/start-a-new-genesis-ledger-in-stand-alone-mode.html>`_
with RPC port exposed and that ``aioxrpy`` package is installed.

On macOS::

    $ docker run -d --name ripple-regtest -p 5005:5005 ulamlabs/ripple-regtest
    $ pip install aioxrpy


Submitting your first transaction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When running Ripple in stand-alone mode, a new genesis ledger is created. A 
hardcoded genesis address holds all 100 billion XRP. Let's start by
initializing a ``RippleKey`` object using master seed for that address::

    master = RippleKey(private_key='snoPBrXtMeMyMHUVTgbuqAfg1SUTb')

For a Ripple account to be active, it needs to be funded with minimum reserve 
amount. If you're submitting your transaction against a regtest node, the
minimum amount is 200 XRP. You won't be able to spend it as it must remain on
your account for it to remain active.

Let's generate the keys for our new account::

    destination = RippleKey()

You can initialize a ``RippleKey`` instance with either a public, private key 
or none. With just a public key, you can't sign a transaction, but you can
verify a transaction signature. Private key accepts either a master seed to 
derive the key from or a private key itself.

Ripple transaction is essentially an action executed on the blockchain. A type
of action is determined by `TransactionType` field. This can be either a
payment, change to the account (ex. changing the keys, nickname and
parameters). If a transaction creates a new object on the ledger, reserve 
amount will be increased. On genesis ledger, that amount is 50 XRP per object.

Transaction object needs to contain at least these fields:

- `Fee` - transaction fee, in drops,
- `Account` - account you're sending the funds from,
- `Sequence` - determines an order in which transactions should be submitted,
- `SigningPubKey` - specifies public key transaction was signed with. In case 
  of multi-signed transaction, it's still required but it should be left empty.
- `TransactionType` - type of transaction.

While `Flags` field is optional, it's recommended to pass
``tfFullyCanonicalSig`` value. This protects the transaction from a malicious
actor being able to modify the signature. The issue is more thoroughly explained
`here <https://xrpl.org/transaction-malleability.html#exploit-with-malleable-transactions>`_.

Depending on a transaction type, additional fields might be required. Let's focus
on a payment in this example.

- `Amount` - amount of XRP (in drops) or issued currency sent in this transaction,
- `Destination` - address which will receive these funds.

Depending on whether the transaction is signed by a single or multiple keys you
need to also pass one of these fields:

- `TxnSignature` - signature for transaction in case of single signature, 
- `Signers` - contains a list of signer objects, sorted by account ID (account name in binary format).

RPC class contains helper methods (``sign_and_submit``, ``multisign_and_submit``)
that will sign and submit it to the node for you. These will also set `Sequence` 
field for you.

::

    rpc = RippleJsonRpc('http://localhost:5005')
    reserve = await rpc.get_reserve()
    fee = await rpc.fee()

    tx = {
        'Account': master.to_account(),
        'Flags': RippleTransactionFlags.FullyCanonicalSig,
        'TransactionType': RippleTransactionType.Payment,
        'Amount': decimals.xrp_to_drops(reserve.base),
        'Destination': destination.to_account(),
        'Fee': fee.minimum
    }

    # post TX blob to rippled JSON-RPC
    result = await rpc.sign_and_submit(tx, master)

``result`` should contain the response from RPC node if transaction was
successfully submitted. Otherwise, the last line will throw an exception.

Example code
^^^^^^^^^^^^

Complete example code::

    import asyncio

    from aioxrpy import decimals
    from aioxrpy.definitions import RippleTransactionType, RippleTransactionFlags
    from aioxrpy.keys import RippleKey
    from aioxrpy.rpc import RippleJsonRpc


    async def example():
        rpc = RippleJsonRpc('http://localhost:5005')
        reserve = await rpc.get_reserve()
        fee = await rpc.fee()

        master = RippleKey(private_key='snoPBrXtMeMyMHUVTgbuqAfg1SUTb')
        destination = RippleKey()

        tx = {
            'Account': master.to_account(),
            'Flags': RippleTransactionFlags.FullyCanonicalSig,
            'TransactionType': RippleTransactionType.Payment,
            'Amount': decimals.xrp_to_drops(reserve.base),
            'Destination': destination.to_account(),
            'Fee': fee.minimum
        }

        # post TX blob to rippled JSON-RPC
        result = await rpc.sign_and_submit(tx, master)
        print(result)


    asyncio.get_event_loop().run_until_complete(example())
