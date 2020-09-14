from __future__ import annotations

import contextlib
import gzip
import io
import itertools
import tempfile
import threading
import zlib
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import AsyncContextManager, Iterator, List, Tuple, Union

import pytest

from cjwmodule.http import HttpError, httpfile
from cjwmodule.testing.i18n import cjwmodule_i18n_message


@dataclass(frozen=True)
class MockHttpResponse:
    status_code: int = 200
    """HTTP status code"""

    headers: List[Tuple[str, str]] = field(default_factory=list)
    """List of headers -- including Content-Length, Transfer-Encoding, etc."""

    body: Union[bytes, List[bytes]] = b""
    """
    HTTP response body.

    If this is `bytes` (including the default, `b""`), then `headers` requires
    a `Content-Length`. If this is a `List[bytes]`, then `headers` requires
    `Transfer-Encoding: chunked`.
    """

    @classmethod
    def ok(
        cls, body: bytes = b"", headers: List[Tuple[str, str]] = []
    ) -> MockHttpResponse:
        if isinstance(body, bytes):
            if not any(h[0].lower() == "content-length" for h in headers):
                # do not append to `headers`: create a new list
                headers = headers + [("content-length", str(len(body)))]
        elif isinstance(body, list):
            if not any(h[0].lower() == "transfer-encoding" for h in headers):
                # do not append to `headers`: create a new list
                headers = headers + [("transfer-encoding", "chunked")]
        else:
            raise TypeError("body must be bytes or List[bytes]; got %r" % type(body))
        return cls(status_code=200, body=body, headers=headers)


@pytest.fixture
def http_server():
    http_server = None
    response: Union[MockHttpResponse, Iterator[MockHttpResponse]] = iter([])

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal http_server
            http_server.requested_paths.append(self.path)

            r = response
            if hasattr(r, "__next__"):
                r = next(r)

            self.send_response_only(r.status_code)
            for header, value in r.headers:
                self.send_header(header, value)
            self.end_headers()
            write = self.wfile.write
            if isinstance(r.body, list):
                # chunked encoding
                for chunk in r.body:
                    write(("%x\r\n" % len(chunk)).encode("ascii"))
                    write(chunk)
                    write(b"\r\n")
                write(b"0\r\n\r\n")
            else:
                # just write the bytes
                write(r.body)

    class HttpServer:
        def __init__(self):
            self.server = HTTPServer(("localhost", 0), Handler)
            self.requested_paths = []

        def mock_response(
            self, new_response: Union[MockHttpResponse, Iterator[MockHttpResponse]]
        ) -> None:
            nonlocal response
            response = new_response

        def build_url(self, path: str) -> str:
            return "http://%s:%d%s" % (*self.server.server_address, path)

        def __enter__(self):
            self.thread = threading.Thread(
                target=self.server.serve_forever, kwargs={"poll_interval": 0.005}
            )
            self.thread.setDaemon(True)
            self.thread.start()
            return self

        def __exit__(self, *exc_info):
            self.server.shutdown()
            self.thread.join()

    with HttpServer() as http_server:
        yield http_server


@pytest.mark.asyncio
class TestDownload:
    @contextlib.asynccontextmanager
    async def download(self, url, **kwargs) -> AsyncContextManager[Path]:
        """
        Convenience method: wrap with a tempfile context and asyncio.run().
        """
        with tempfile.NamedTemporaryFile() as tf:
            path = Path(tf.name)
            await httpfile.download(url, path, **kwargs)
            yield path

    async def test_raw_bytes(self, http_server):
        # This is the only test that checks raw output. Other tests simply
        # check that httpfile.read() does what we expect.
        body = b"A,B\nx,y\nz,a"
        url = http_server.build_url("/path/to.csv")
        http_server.mock_response(
            MockHttpResponse.ok(body, [("content-type", "text/csv; charset=utf-8")])
        )
        async with self.download(url) as path:
            with gzip.GzipFile(path) as zf:
                assert zf.read() == b"\r\n".join(
                    [
                        ('{"url":"%s"}' % url).encode("utf-8"),
                        b"200 OK",
                        b"content-type: text/csv; charset=utf-8",
                        b"Cjw-Original-content-length: 11",
                        b"",
                        b"A,B\nx,y\nz,a",
                    ]
                )
                assert zf.mtime == 0

    async def test_raw_bytes_are_deterministic(self, http_server):
        # This is the only test that checks raw output. Other tests simply
        # check that httpfile.read() does what we expect.
        body = b"A,B\nx,y\nz,a"
        url = http_server.build_url("/path/to.csv")
        http_server.mock_response(
            MockHttpResponse.ok(body, [("content-type", "text/csv; charset=utf-8")])
        )
        # download to two separate filenames
        async with self.download(url) as path1, self.download(url) as path2:
            assert path1.read_bytes() == path2.read_bytes()

    async def test_gunzip_encoded_body(self, http_server):
        body = b"A,B\nx,y\nz,a"
        gzbody = gzip.compress(body)
        url = http_server.build_url("/path/to.csv.gz")
        http_server.mock_response(
            MockHttpResponse.ok(
                gzbody,
                [
                    ("content-type", "text/csv; charset=utf-8"),
                    ("content-encoding", "gzip"),
                ],
            )
        )
        async with self.download(url) as path:
            assert b"\r\nCjw-Original-content-encoding: gzip\r\n" in gzip.decompress(
                path.read_bytes()
            )
            with httpfile.read(path) as (parameters, status_line, headers, body_path):
                assert body_path.read_bytes() == body
                assert headers == [
                    ("content-type", "text/csv; charset=utf-8"),
                    ("content-encoding", "gzip"),
                    ("content-length", str(len(gzbody))),
                ]

    async def test_deflate_encoded_body(self, http_server):
        body = b"A,B\nx,y\nz,a"
        zo = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        zbody = zo.compress(body) + zo.flush()
        url = http_server.build_url("/path/to.csv.gz")
        http_server.mock_response(
            MockHttpResponse.ok(
                zbody,
                [
                    ("content-type", "text/csv; charset=utf-8"),
                    ("content-encoding", "deflate"),
                ],
            )
        )
        async with self.download(url) as path:
            assert b"\r\nCjw-Original-content-encoding: deflate\r\n" in gzip.decompress(
                path.read_bytes()
            )
            with httpfile.read(path) as (parameters, status_line, headers, body_path):
                assert body_path.read_bytes() == body
                assert headers == [
                    ("content-type", "text/csv; charset=utf-8"),
                    ("content-encoding", "deflate"),
                    ("content-length", str(len(zbody))),
                ]

    async def test_decode_chunked_csv(self, http_server):
        http_server.mock_response(
            MockHttpResponse.ok(
                [b"A,B\nx", b",y\nz,", b"a"],
                [("content-type", "text/csv; charset=utf-8")],
            )
        )
        url = http_server.build_url("/path/to.csv.chunks")
        async with self.download(url) as path:
            assert (
                b"\r\nCjw-Original-transfer-encoding: chunked\r\n"
                in gzip.decompress(path.read_bytes())
            )
            with httpfile.read(path) as (parameters, status_line, headers, body_path):
                assert body_path.read_bytes() == b"A,B\nx,y\nz,a"
                assert headers == [
                    ("content-type", "text/csv; charset=utf-8"),
                    ("transfer-encoding", "chunked"),
                ]

    async def test_write_latin1_content_disposition(self, http_server):
        # If a server responds with a non-ACSII Content-Definition, write it.
        #
        # In practice, this is _usually_ a bug on the server -- for instance,
        # `Content-disposition: attachment; filename="Зараховані..."`. Nobody
        # actually wants iso-8859-1 encoding because it doesn't handle Unicode.
        # And anybody who thinks about this uses RFC6266 to encode
        # Content-Disposition. But all we're testing is that we don't crash.
        #
        # https://www.pivotaltracker.com/story/show/174715741
        body = b"A,B\nx,y\nz,a"
        url = http_server.build_url("/path/to.csv")
        # erroneous value, seen in the wild
        # 'Зараховані.json'.encode('utf-8').decode('latin1')
        latin1_header = 'attachment; filename="Ð\x97Ð°Ñ\x80Ð°Ñ\x85Ð¾Ð²Ð°Ð½Ñ\x96.json"'
        http_server.mock_response(
            MockHttpResponse.ok(
                body,
                [
                    ("content-type", "text/csv; charset=utf-8"),
                    ("content-disposition", latin1_header),
                ],
            )
        )
        async with self.download(url) as path:
            # 'Зараховані.json'.encode('utf-8')
            #
            # ... we're testing that the file contains latin1. This bizarre
            # string looks like UTF-8, but httpfile will return it as latin1.
            assert (
                b'\r\ncontent-disposition: attachment; filename="\xd0\x97\xd0\xb0\xd1\x80\xd0\xb0\xd1\x85\xd0\xbe\xd0\xb2\xd0\xb0\xd0\xbd\xd1\x96.json"\r\n'
                in gzip.decompress(path.read_bytes())
            )

    async def test_404_http_error(self, http_server):
        http_server.mock_response(MockHttpResponse(404))
        with pytest.raises(HttpError.NotSuccess) as cm:
            await httpfile.download(http_server.build_url("/not-found"), Path())
        assert cm.value.i18n_message == cjwmodule_i18n_message(
            "http.errors.HttpErrorNotSuccess",
            {"status_code": 404, "reason": "Not Found"},
        )

    async def test_invalid_url(self):
        with pytest.raises(HttpError.InvalidUrl):
            await httpfile.download("-", Path())

    async def test_unsupported_protocol(self):
        with pytest.raises(HttpError.InvalidUrl):
            await httpfile.download("htt://example.com", Path())

    async def test_follow_redirect(self, http_server):
        url1 = http_server.build_url("/url1.csv")
        url2 = http_server.build_url("/url2.csv")
        url3 = http_server.build_url("/url3.csv")
        http_server.mock_response(
            iter(
                [
                    MockHttpResponse(302, [("location", url2)]),
                    MockHttpResponse(302, [("location", url3)]),
                    MockHttpResponse.ok(b"A,B\n1,2", [("content-type", "text/csv")]),
                ]
            )
        )
        async with self.download(url1) as path:
            with httpfile.read(path) as (parameters, status_line, headers, body_path):
                assert body_path.read_bytes() == b"A,B\n1,2"
        assert http_server.requested_paths == ["/url1.csv", "/url2.csv", "/url3.csv"]

    async def test_redirect_loop(self, http_server):
        url1 = http_server.build_url("/url1.csv")
        url2 = http_server.build_url("/url2.csv")
        http_server.mock_response(
            itertools.cycle(
                [
                    MockHttpResponse(302, [("location", url2)]),
                    MockHttpResponse(302, [("location", url1)]),
                ]
            )
        )
        with pytest.raises(HttpError.TooManyRedirects):
            async with self.download(url1):
                pass

    async def test_generic_http_error(self, http_server):
        url = http_server.build_url("/should-be-gzipped")
        http_server.mock_response(
            MockHttpResponse.ok(b"not gzipped", [("content-encoding", "gzip")])
        )
        with pytest.raises(HttpError.Generic) as cm:
            async with self.download(url):
                pass
        assert cm.value.i18n_message == cjwmodule_i18n_message(
            "http.errors.HttpErrorGeneric", {"type": "DecodingError"}
        )


class TestRead:
    def test_happy_path(self):
        with tempfile.NamedTemporaryFile() as tf:
            path = Path(tf.name)
            path.write_bytes(
                gzip.compress(
                    b"".join(
                        [
                            b'{"url":"http://example.com/hello"}\r\n',
                            b"200 OK\r\n",
                            b"content-type: text/plain; charset=utf-8\r\n",
                            b"content-disposition: inline\r\n",
                            b"\r\n",
                            b"Some text",
                        ]
                    )
                )
            )
            with httpfile.read(path) as (parameters, status_line, headers, body_path):
                assert parameters == {"url": "http://example.com/hello"}
                assert status_line == "200 OK"
                assert headers == [
                    ("content-type", "text/plain; charset=utf-8"),
                    ("content-disposition", "inline"),
                ]
                assert body_path.read_bytes() == b"Some text"

    def test_latin1_headers(self):
        with tempfile.NamedTemporaryFile() as tf:
            path = Path(tf.name)
            path.write_bytes(
                gzip.compress(
                    b"".join(
                        [
                            b'{"url":"http://example.com/hello"}\r\n',
                            b"200 OK\r\n",
                            b"content-disposition: attachment; filename=caf\xe9\r\n",
                            b"\r\n",
                            b"Some text",
                        ]
                    )
                )
            )
            with httpfile.read(path) as (parameters, status_line, headers, body_path):
                assert headers == [("content-disposition", "attachment; filename=café")]

    def test_do_not_crash_on_utf8_encoded_content_disposition_header(self):
        # If the server responded with a UTF-8-encoded header, that's a bug
        # on the server: the author didn't realize all headers are
        # latin1-encoded, so the header is actually double-encoded.
        #
        # The result: if a developer unwittingly utf8-encodes a filename, then
        # the result is _unambiguously_ something else. For instance, "café"
        # encodes to "cafÃ©".
        #
        # We're spec-compliant here. We will correctly return "cafÃ©". The
        # caller can second-guess us if it sees fit.
        #
        # https://www.pivotaltracker.com/story/show/174715741
        with tempfile.NamedTemporaryFile() as tf:
            path = Path(tf.name)
            path.write_bytes(
                gzip.compress(
                    b"".join(
                        [
                            b'{"url":"http://example.com/hello"}\r\n',
                            b"200 OK\r\n",
                            b"content-disposition: attachment; filename=caf\xc3\xa9\r\n",
                            b"\r\n",
                            b"Some text",
                        ]
                    )
                )
            )
            with httpfile.read(path) as (parameters, status_line, headers, body_path):
                assert headers == [
                    ("content-disposition", "attachment; filename=cafÃ©")
                ]

    def test_special_headers(self):
        # Content-Length doesn't get stored in the httpfile format, because it
        # would be ambiguous. (It does not specify the number of bytes of body.
        # That's because httpfile stores *decoded* body, and it stores headers
        # as passed over HTTP.)
        with tempfile.NamedTemporaryFile() as tf:
            path = Path(tf.name)
            path.write_bytes(
                gzip.compress(
                    b'{"url":"http://example.com/hello"}\r\n'
                    b"200 OK\r\n"
                    b"Cjw-Original-content-length: 9\r\n"
                    b"\r\n"
                    b"Some text"
                )
            )
            with httpfile.read(path) as (parameters, status_line, headers, body_path):
                assert headers == [("content-length", "9")]


class TestWrite:
    def test_prefix_special_headers(self):
        # Content-Length doesn't get stored in the httpfile format, because it
        # would be ambiguous. (It does not specify the number of bytes of body.
        # That's because httpfile stores *decoded* body, and it stores headers
        # as passed over HTTP.)
        with tempfile.NamedTemporaryFile() as tf:
            path = Path(tf.name)
            httpfile.write(
                Path(tf.name),
                {"url": "http://example.com/hello"},
                "200 OK",
                [
                    ("transfer-encoding", "chunked"),
                    ("content-encoding", "gzip"),
                    ("content-length", "3"),
                ],
                io.BytesIO(b"\x00\x01\x02"),
            )
            assert gzip.decompress(path.read_bytes()) == (
                b'{"url":"http://example.com/hello"}\r\n'
                b"200 OK\r\n"
                b"Cjw-Original-transfer-encoding: chunked\r\n"
                b"Cjw-Original-content-encoding: gzip\r\n"
                b"Cjw-Original-content-length: 3\r\n"
                b"\r\n"
                b"\x00\x01\x02"
            )

    def test_ignore_most_headers(self):
        # a header like "ETag", "Date" or "Last-Modified" is unreliable. It
        # doesn't reliably indicate new data from the server. On the flipside,
        # it _does_ mean that two files won't compare as equivalent. So we
        # nix these headers.
        with tempfile.NamedTemporaryFile() as tf:
            path = Path(tf.name)
            httpfile.write(
                path,
                {"url": "http://example.com/hello"},
                "200 OK",
                [
                    ("date", "Wed, 21 Oct 2015 07:28:00 GMT"),
                    ("server", "custom-server 0.1"),
                    ("ETag", "some-etag"),
                ],
                io.BytesIO(b"\x00\x01\x02"),
            )
            assert gzip.decompress(path.read_bytes()) == (
                b'{"url":"http://example.com/hello"}\r\n'
                b"200 OK\r\n"
                b"server: custom-server 0.1\r\n"
                b"\r\n"
                b"\x00\x01\x02"
            )
