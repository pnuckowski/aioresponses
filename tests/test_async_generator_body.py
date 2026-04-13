import pytest
from aiohttp import ClientSession

from aioresponses import aioresponses


@pytest.mark.asyncio
async def test_async_generator_body_exception():
    url = "http://1.2.3.4"
    with aioresponses() as m:
        m.post(url)

        async def data_generator():
            yield b"foo"
            raise RuntimeError("this generator is never awaited")

        with pytest.raises(RuntimeError, match="never awaited"):
            async with ClientSession() as session:
                async with session.post(url, data=data_generator()) as resp:
                    await resp.text()
