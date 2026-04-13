"""
Tests for the aioresponses pytest plugin (aioresponse fixture).
"""
import aiohttp
import pytest
from aiohttp.client_exceptions import ClientConnectionError


async def test_plugin_fixture_get(aioresponse):
    m = aioresponse()
    m.get("http://example.com/api", status=200)

    async with aiohttp.ClientSession() as session:
        resp = await session.get("http://example.com/api")

    assert resp.status == 200


async def test_plugin_fixture_post(aioresponse):
    m = aioresponse()
    m.post("http://example.com/api", status=201, payload={"id": 1})

    async with aiohttp.ClientSession() as session:
        resp = await session.post("http://example.com/api")
        data = await resp.json()

    assert resp.status == 201
    assert data == {"id": 1}


async def test_plugin_fixture_multiple_calls(aioresponse):
    m = aioresponse()
    m.get("http://example.com/api", status=200)
    m.get("http://example.com/api", status=404)

    async with aiohttp.ClientSession() as session:
        r1 = await session.get("http://example.com/api")
        r2 = await session.get("http://example.com/api")

    assert r1.status == 200
    assert r2.status == 404


async def test_plugin_fixture_passthrough_unmatched(aioresponse):
    """Factory allows passing kwargs like passthrough_unmatched."""
    matched_url = "http://example.com/mocked"
    unmatched_url = "https://httpbin.org/get"

    m = aioresponse(passthrough_unmatched=True)
    m.get(matched_url, status=200)

    async with aiohttp.ClientSession() as session:
        mocked_resp = await session.get(matched_url)
        real_resp = await session.get(unmatched_url)

    assert mocked_resp.status == 200
    assert real_resp.status == 200


async def test_plugin_fixture_passthrough_list(aioresponse):
    """Factory allows passing passthrough list."""
    external = "https://httpbin.org/status/201"
    mocked = "http://example.com/api"

    m = aioresponse(passthrough=[external])
    m.get(mocked, status=200)

    async with aiohttp.ClientSession() as session:
        mocked_resp = await session.get(mocked)
        real_resp = await session.get(external)

    assert mocked_resp.status == 200
    assert real_resp.status == 201


async def test_plugin_fixture_unmatched_raises_by_default(aioresponse):
    """Without passthrough_unmatched, unmatched requests raise ClientConnectionError."""
    m = aioresponse()
    m.get("http://example.com/api", status=200)

    async with aiohttp.ClientSession() as session:
        with pytest.raises(ClientConnectionError):
            await session.get("http://example.com/other")



