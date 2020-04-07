from dataclasses import dataclass

from aiohttp.client import ClientSession

from aioxrpy import exceptions
from aioxrpy.definitions import RippleTransactionResultCategory


@dataclass
class RippleReserveInfo:
    base: int
    inc: int


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

    async def fee(self):
        return await self.post('fee')

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
        Submits transaction to JSON-RPC and handles `engine_result` value,
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
