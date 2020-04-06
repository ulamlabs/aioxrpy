import asyncio

from aioresponses import aioresponses
import pytest

from aioxrpy import exceptions
from aioxrpy.rpc import RippleJsonRpc


@pytest.fixture
def rpc():
    return RippleJsonRpc('http://mock.rpc.url')


@pytest.fixture
def mock_post(mocker, rpc):
    return mocker.patch.object(
        rpc, 'post', side_effect=asyncio.coroutine(lambda *args, **kwargs: {})
    )


@pytest.fixture
def ar():
    with aioresponses() as m:
        yield m


async def test_error_mapping(rpc, ar):
    # known exception
    ar.post(rpc.URL, payload={'result': {'error': 'actNotFound'}})
    with pytest.raises(exceptions.AccountNotFoundException):
        await rpc.post('account_info', {'account': 'wrongname'})

    # unknown exception
    ar.post(rpc.URL, payload={'result': {'error': 'everythingIsFine'}})
    with pytest.raises(exceptions.UnknownRippleException):
        await rpc.post('fee')

    payload = {
        'drops': {
            'minimum_fee': '10'
        }
    }
    ar.post(rpc.URL, payload={'result': payload})
    assert await rpc.post('fee') == payload


async def test_fee(rpc, mock_post):
    await rpc.fee()
    mock_post.assert_called_with('fee')


async def test_ledger(rpc, mock_post):
    await rpc.ledger(123)
    mock_post.assert_called_with('ledger', {'ledger_index': 123})


async def test_ledger_accept(rpc, mock_post):
    await rpc.ledger_accept()
    mock_post.assert_called_with('ledger_accept')


async def test_ledger_closed(rpc, mock_post):
    await rpc.ledger_closed()
    mock_post.assert_called_with('ledger_closed')


async def test_submit(rpc, mock_post):
    response = {
        'engine_result': 'tesSUCCESS'
    }
    mock_post.side_effect = asyncio.coroutine(lambda *args, **kwargs: response)
    assert await rpc.submit('0123ffc') == response
    mock_post.assert_called_with('submit', {'tx_blob': '0123ffc'})


async def test_submit_error_mapping(rpc, mock_post):
    response = {
        'engine_result': 'tecNO_DST_INSUF_XRP'
    }
    mock_post.side_effect = asyncio.coroutine(lambda *args, **kwargs: response)
    with pytest.raises(exceptions.RippleTransactionCostlyFailureException):
        await rpc.submit('0123ffc')
    mock_post.assert_called_with('submit', {'tx_blob': '0123ffc'})


async def test_server_info(rpc, mock_post):
    response = {
        'info': {
            'validated_ledger': {}
        }
    }
    mock_post.side_effect = asyncio.coroutine(lambda *args, **kwargs: response)
    assert await rpc.server_info() == response['info']
    mock_post.assert_called_with('server_info')
