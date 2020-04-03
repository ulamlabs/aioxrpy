from decimal import Decimal as D

from aiohttp.client import ClientSession

from aioxrpy.exceptions import ripple_error_to_exception


def xrp_to_drops(amount):
    return int((D(1000000) * amount).quantize(D('1')))


def drops_to_xrp(amount):
    return D(amount) / D(1000000)


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
                    raise ripple_error_to_exception(error)
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
        return await self.post('submit', {'tx_blob': tx_blob})

    async def server_info(self):
        return (await self.post('server_info'))['info']
