import json

import pytest

from martin_eden.core import HttpMessageHandler
from martin_eden.http_utils import HttpHeadersParser
from martin_eden.routing import register_route
from tests.conftest import base_http_request, base_http_result_headers

pytest_plugins = ('pytest_asyncio',)


@register_route('/test/', 'get')
async def get_openapi_schema() -> str:
    return 'test'


@pytest.fixture
def http_get_request():
    return base_http_request.encode('utf8')


@pytest.fixture
def http_headers():
    return base_http_result_headers.encode('utf8')


@pytest.fixture
def content_type():
    return b'Content-Type: application/json;charset=UTF-8\n\n'


@pytest.mark.asyncio
async def test_not_existing_url(http_get_request, http_headers, content_type):
    http_headers = (
        http_headers[:-1] +
        content_type +
        b'404 not found'
    )

    handler = HttpMessageHandler(http_get_request)
    response = await handler.handle_request()

    assert response == http_headers


@pytest.mark.asyncio
async def test_existing_url(http_get_request, http_headers, content_type):
    http_headers = (
        http_headers[:-1] +
        content_type +
        b'test'
    )
    http_get_request = http_get_request.replace(b'/users/', b'/test/')

    handler = HttpMessageHandler(http_get_request)
    response = await handler.handle_request()

    assert response == http_headers


@pytest.mark.asyncio
async def test_options_method(http_get_request, http_headers):
    http_get_request = (
        http_get_request
        .replace(b'GET', b'OPTIONS')
        .replace(b'/users/', b'/test/')
    )
    http_headers = (
        http_headers[:-1] +
        b'Allow: OPTIONS, GET, POST\n\n'
    )
    handler = HttpMessageHandler(http_get_request)
    response = await handler.handle_request()

    assert response == http_headers


@pytest.mark.asyncio
async def test_openapi_schema(http_get_request):
    http_get_request = http_get_request.replace(b'/users/', b'/schema/')

    handler = HttpMessageHandler(http_get_request)
    response = await handler.handle_request()

    parser = HttpHeadersParser(response.decode('utf8'))
    openapi_result = json.loads(parser.body)
    assert openapi_result['paths'] == {
        '/test/': {'get': {'operationId': 'test_get'}}
    }