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

## Usage

### Keys

Signing and verifying transactions, as well as generating new accounts is done through `RippleKey` class. 

```
from aioxrpy.keys import RippleKey

# New key
key = RippleKey()

# From public key
key = RippleKey(public_key=b'public key')

# From master seed
key = RippleKey(private_key='seed')

# From private key
key = RippleKey(private_key=b'private key')
```

Such key can be converted to Account ID and public key. 

### Submitting transactions

RPC client provides a helper which signs and submits transaction. As a first 
argument it takes a transaction dict. The second one is a `RippleKey` instance
used for signing this transaction.

```
from aioxrpy.rpc import RippleJsonRpc

rpc = RippleJsonRpc(url)
await rpc.sign_and_submit(
    {
        'Account': account,
        'TransactionType': RippleTransactionType.Payment,
        'Amount': decimals.xrp_to_drops(200),
        'Destination': destination,
        'Fee': 10
    },
    signer
)
```

### Multi-signed transactions

RPC client provides a helper which signs and submits transaction using multiple
keys. As a second argument, it expects a list of `RippleKey` instances. Please 
don't forget that each signer increases transaction fees.

```
from aioxrpy.rpc import RippleJsonRpc

rpc = RippleJsonRpc(url)
await rpc.multisign_and_submit(
    {
        'Account': account,
        'TransactionType': RippleTransactionType.Payment,
        'Amount': decimals.xrp_to_drops(200),
        'Destination': destination,
        'Fee': 30
    },
    [signer_1, signer_2]
)
```

## Documentation

Docs and usage examples are available [here](https://aioxrpy.readthedocs.io/en/latest).

## Unit testing

To run unit tests, you need to bootstrap a Rippled regtest node first. Use the provided `docker-compose.yml` file.

```
$ docker-compose up -d
```
