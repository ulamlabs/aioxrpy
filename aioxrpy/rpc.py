import binascii
from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List

from aiohttp.client import ClientSession

from aioxrpy import address, exceptions, serializer
from aioxrpy.definitions import RippleTransactionResultCategory
from aioxrpy.keys import RippleKey


@dataclass
class RippleReserveInfo:
    base: int
    inc: int


@dataclass
class RippleFeeInfo:
    base: int
    median: int
    minimum: int
    open_ledger: int


class RippleJsonRpc:
    def __init__(self, url):
        self.URL = url

    async def post(self, method, *args):
        async with ClientSession() as session:
            async with session.post(
                self.URL,
                json={
                    'method': method,
                    'params': list(args)
                }
            ) as res:
                resp_dict = await res.json(content_type=None)
                result = resp_dict.get('result')
                error = result.get('error')
                if error:
                    raise {
                        'actNotFound': exceptions.AccountNotFoundException,
                        'invalidTransaction': (
                            exceptions.InvalidTransactionException
                        )
                    }.get(error, exceptions.UnknownRippleException)(result)
                return result

    async def account_info(self, account, ledger_index='closed'):
        return await self.post('account_info', {
            'account': account,
            'ledger_index': ledger_index
        })

    async def fee(self) -> RippleFeeInfo:
        result = await self.post('fee')
        drops = result.get('drops', {})
        return RippleFeeInfo(
            base=int(drops.get('base_fee', '10')),
            median=int(drops.get('median_fee', '10')),
            minimum=int(drops.get('minimum_fee', '10')),
            open_ledger=int(drops.get('open_ledger_fee', '10'))
        )

    async def ledger(self, index, **kwargs):
        return await self.post('ledger', {
            'ledger_index': index,
            **kwargs
        })

    async def ledger_accept(self):
        return await self.post('ledger_accept')

    async def ledger_closed(self):
        return await self.post('ledger_closed')

    async def submit(self, tx_blob):
        """
        Submits raw transaction to JSON-RPC and handles `engine_result` value,
        mapping error codes to exceptions
        """
        result = await self.post('submit', {'tx_blob': tx_blob})
        engine_result = result.get('engine_result')
        category, code = engine_result[:3], engine_result[3:]

        if category != RippleTransactionResultCategory.Success:
            # Map category to exception
            raise {
                RippleTransactionResultCategory.CostlyFailure: (
                    exceptions.RippleTransactionCostlyFailureException
                ),
                RippleTransactionResultCategory.LocalFailure: (
                    exceptions.RippleTransactionLocalFailureException
                ),
                RippleTransactionResultCategory.MalformedFailure: (
                    exceptions.RippleTransactionMalformedException
                ),
                RippleTransactionResultCategory.RetriableFailure: (
                    exceptions.RippleTransactionRetriableException
                ),
                RippleTransactionResultCategory.Failure: (
                    exceptions.RippleTransactionFailureException
                )
            }[category](code)

        return result

    async def sign_and_submit(self, tx: dict, key: RippleKey) -> dict:
        """
        Signs, serializes and submits the transaction using provided key
        """
        tx = deepcopy(tx)

        if 'SigningPubKey' not in tx:
            tx['SigningPubKey'] = key.to_public()

        if 'Sequence' not in tx:
            info = await self.account_info(
                tx['Account'], ledger_index='current'
            )
            tx['Sequence'] = info['account_data']['Sequence']

        tx['TxnSignature'] = key.sign_tx(tx)
        tx_blob = binascii.hexlify(serializer.serialize(tx)).decode()
        return await self.submit(tx_blob)

    async def multisign_and_submit(
        self, tx: Dict, keys: List[RippleKey]
    ) -> dict:
        """
        Signs, serializes and submits the transaction using multiple
        keys
        """
        tx = deepcopy(tx)
        assert 'Account' in tx

        if 'Sequence' not in tx:
            info = await self.account_info(
                tx['Account'], ledger_index='current'
            )
            tx['Sequence'] = info['account_data']['Sequence']

        # sort keys by account ID
        tx['SigningPubKey'] = b''
        tx['Signers'] = [
            {
                'Signer': {
                    'Account': key.to_account(),
                    'TxnSignature': key.sign_tx(tx, multi_sign=True),
                    'SigningPubKey': key.to_public(),
                }
            }
            for key in sorted(
                keys, key=lambda key: address.decode_address(key.to_account())
            )
        ]
        tx_blob = binascii.hexlify(serializer.serialize(tx)).decode()
        return await self.submit(tx_blob)

    async def server_info(self):
        return (await self.post('server_info'))['info']

    async def get_reserve(self) -> RippleReserveInfo:
        result = await self.server_info()
        validated_ledger = result.get('validated_ledger')
        if not validated_ledger:
            raise exceptions.ValidatedLedgerUnavailableException

        return RippleReserveInfo(
            base=validated_ledger['reserve_base_xrp'],
            inc=validated_ledger['reserve_inc_xrp']
        )
