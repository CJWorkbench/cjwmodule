import asyncio
import io
import struct

import _socket
import pytest

from cjwmodule.http.client import download
from cjwmodule.http.errors import HttpError


@pytest.mark.asyncio
async def test_download_stream_connection_reset():
    async def respond_then_die(reader, writer):
        # Read request -- as we should
        await reader.readuntil(b"\r\n\r\n")
        # Send HTTP header and start sending data -- so the client is streaming
        writer.write(
            b"HTTP/1.1 200 OK\r\nContent-Length:1000\r\nContent-Type:text/plain\r\n\r\nstart"
        )
        await writer.drain()
        # Now force a TCP RST packet, which will cause response.aclose() to fail
        # http://deepix.github.io/2016/10/21/tcprst.html
        fd = writer._transport._sock.fileno()
        linger = struct.pack("=II", 1, 0)
        _socket.socket(fileno=fd).setsockopt(
            _socket.SOL_SOCKET, _socket.SO_LINGER, bytearray(linger)
        )
        writer.close()

    server = await asyncio.start_server(
        respond_then_die, "127.0.0.1", 0, start_serving=True
    )
    async with server:
        host, port = server.sockets[0].getsockname()
        with pytest.raises(HttpError.Generic):
            await download(f"http://{host}:{port}/data", io.BytesIO())
