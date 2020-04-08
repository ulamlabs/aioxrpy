# aioxrpy

[![Documentation Status](https://readthedocs.org/projects/aioxrpy/badge/?version=latest)](http://aioxrpy.readthedocs.io/en/latest/?badge=latest) [![codecov](https://codecov.io/gh/ulamlabs/aioxrpy/branch/master/graph/badge.svg)](https://codecov.io/gh/ulamlabs/aioxrpy) ![Python package](https://github.com/ulamlabs/aioxrpy/workflows/Python%20package/badge.svg) ![Upload Python Package](https://github.com/ulamlabs/aioxrpy/workflows/Upload%20Python%20Package/badge.svg)

Ripple blockchain library for Python.

## Features

1. Async JSON-RPC client.
2. Signing and verifying transactions using private and public keys.
3. Support for signing transactions with multiple keys.
4. Serializer and deserializer for Ripple objects.

## Installation

Library is available on PyPi, you can simply install it using `pip`.
```
$ pip install aioxrpy
```

## Example

```
sender = RippleKey(private_key=sender_key)
rpc = RippleJsonRpc(rpc_url)

await rpc.sign_and_submit(
    {
        'Account': sender.to_account(),
        'Flags': RippleTransactionFlags.FullyCanonicalSig,
        'TransactionType': RippleTransactionType.Payment,
        'Amount': decimals.xrp_to_drops(200),
        'Destination': 'rhpu8AZJKnLsxXqPiqsShp5svttVWhwQbG',
        'Fee': 10
    },
    sender
)
```

## Documentation

Docs and usage examples are available [here](https://aioxrpy.readthedocs.io/en/latest).

## Unit testing

To run unit tests, you need to bootstrap a Rippled regtest node first. Use the provided `docker-compose.yml` file.

```
$ docker-compose up -d
```
