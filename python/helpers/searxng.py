import aiohttp
from python.helpers import tls as _tls
from python.helpers import runtime

URL = "http://localhost:55510/search"

async def search(query:str):
    return await runtime.call_development_function(_search, query=query)

async def _search(query:str):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(**_tls.get_aiohttp_connector_kwargs())) as session:
        async with session.post(URL, data={"q": query, "format": "json"}) as response:
            return await response.json()
