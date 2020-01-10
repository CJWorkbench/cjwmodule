r"""
Fetch data using HTTP, then parse it.

Behavior
--------

a. Perform an HTTP request and log traffic (gzipped) to output_file
b. If the server responds with a redirect, truncate output_file and restart
c. If there's an error or timeout, truncate output_file and raise error

File format
-----------

In case of success, a special HTTP log is written to a *gzipped* file:

    {"url":"https://example.com/test.csv"}\r\n
    200 OK\r\n
    Response-Header-1: X\r\n
    Response-Header-2: Y\r\n
    \r\n
    All body bytes

`Transfer-Encoding`, `Content-Encoding` and `Content-Length` headers are
renamed `Cjw-Original-Transfer-Encoding`, `Cjw-Original-Content-Encoding`
and `Cjw-Original-Content-Length`. (The body in the HTTP log is dechunked
and decompressed, because Python's ecosystem doesn't have nice options for
storing raw HTTP traffic and dechunking from a file.)

The params in the first line are UTF-8-encoded with no added whitespace
(so "\r\n" cannot appear); status is ASCII-encoded; headers are
latin1-encoded; the body is raw. (Rationale: each encoding is the content's
native encoding.)

SECURITY: we don't store the request HTTP headers, because they may contain
OAuth tokens or API keys.

Rationale for storing params: it avoids a race in which we render with new
params but an old fetch result. We only store the "fetch params" ("url"),
not the "render params" ("has_header"), so the file is byte-for-byte identical
when we fetch an unchanged URL with new render params.

In case of redirect, only the last request is logged.
"""

import contextlib
import gzip
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO, ContextManager, List, Optional, Tuple

from . import client

__all__ = ["read", "write", "download", "extract_first_header"]
_HEADER_PATTERN = re.compile(": *")


def write(
    f: BinaryIO,
    url: str,
    status_line: str,
    headers: List[Tuple[str, str]],
    body: BinaryIO,
) -> None:
    """
    Write httpfile-formatted data to `f`.

    This module's docstring describes the file format.
    """
    # set gzip mtime=0 so we can write the exact same file given the exact
    # same data. (This helps with testing and versioning.)
    with gzip.GzipFile(mode="wb", filename="", fileobj=f, mtime=0) as zf:
        # Write URL -- original URL, not redirected URL
        zf.write(
            json.dumps(
                {"url": url},  # SECURITY: don't store "headers" secrets
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            + b"\r\n"
        )
        # Write status line
        zf.write(status_line.encode("utf-8"))
        zf.write(b"\r\n")
        # Write response headers.
        for k, v in headers:
            # body is already dechunked and decompressed. Mangle
            # these headers to make file consistent with itself.
            if k.lower() in {"transfer-encoding", "content-encoding", "content-length"}:
                k = "Cjw-Original-" + k
            elif k.lower() not in {"content-type", "content-disposition", "server"}:
                # Skip writing most headers. This is a HACK: we skip the
                # `Date` header so fetcher will see a byte-for-byte
                # identical output file given byte-for-byte identical
                # input. That will convince fetcher to ignore the result.
                # See `fetcher.versions`. TODO redefine "versions" and
                # revisit this logic: the user probably _expects_ us to
                # store headers every fetch, though body may not change.
                continue
            # There's no way to put \r\n in an HTTP header name or value.
            # Good thing: if a server could do that, this file format would
            # be unreadable.
            assert "\n" not in k and "\n" not in v
            zf.write(f"{k}: {v}\r\n".encode("latin1"))
        zf.write(b"\r\n")

        # Write body
        shutil.copyfileobj(body, zf)


async def download(url: str, output_path: Path, **kwargs) -> None:
    """
    Download from `url` to an httpfile-format file.

    This module's docstring describes the file format.

    Raise HttpError if download fails.
    """
    with tempfile.TemporaryFile() as tf:
        status_code, reason_phrase, headers = await client.download(
            url, tf, **kwargs
        )  # or raise HttpError
        tf.seek(0)

        # The following shouldn't ever error.
        with output_path.open("wb") as f:
            write(f, url, "%d %s" % (status_code, reason_phrase), headers, tf)


@contextlib.contextmanager
def read(
    httpfile_path: Path,
) -> ContextManager[Tuple[Path, str, List[Tuple[str, str]]]]:
    r"""
    Yield `(body: Path, url: str, headers: str)` by parsing `httpfile_path`.

    The yielded `body` contains the downloaded HTTP body. The body is decoded
    according to the HTTP server's `Content-Encoding` and `Transfer-Encoding`.

    The yielded `str` contains HTTP-encoded headers. They are separated by \r\n
    and the final line ends with \r\n. Their `Content-Encoding`,
    `Transfer-Encoding` and `Content-Length` headers are _not_ prefixed with
    `Cjw-Original-`. Do not use these headers to validate `body`, because
    `body` is already decoded.
    """
    with tempfile.NamedTemporaryFile(prefix="body-") as body_f:
        with httpfile_path.open("rb") as f, gzip.GzipFile(mode="rb", fileobj=f) as zf:
            # read params (line 1)
            fetch_params_json = zf.readline()
            fetch_params = json.loads(fetch_params_json)
            url = fetch_params["url"]

            # read and skip status (line 2)
            zf.readline()

            # read headers (lines ending in "\r\n" plus one final "\r\n")
            headers = []
            while True:
                line = zf.readline().decode("latin1").strip()  # strip "\r\n"
                if not line:
                    # "\r\n" on its own line means "end of headers"
                    break
                if line.startswith("Cjw-Original-"):
                    line = line[len("Cjw-Original-") :]
                header, value = _HEADER_PATTERN.split(line, 1)
                headers.append((header, value))

            # Read body into tempfile
            shutil.copyfileobj(zf, body_f)
            body_f.flush()

        # Yield
        yield Path(body_f.name), url, headers


def extract_first_header(headers: List[Tuple[str, str]], header: str) -> Optional[str]:
    r"""
    Scan `headers` for a (case-insensitive) `header`; return its value.

    `headers` must be in the format yielded by `read()`.

    >>> headers = [("Content-Type", "text/plain; charset=utf-8"), ("X-Foo", "Bar"), ("X-Foo", "Baz")]

    Searches are case-insensitive:
    >>> extract_first_header(headers, "content-type")
    "text/plain; charset=utf-8"

    If a header is repeated, only the first value is returned:
    >>> extract_first_header(headers, "x-foo")
    "Bar"

    If a header is missing, return `None`:
    >>> extract_first_header(headers, "content-length")
    None
    """
    # Assume headers are well-formed: otherwise we wouldn't have written them
    # to the `headers` value we're parsing here.
    key = header.upper()
    for header, value in headers:
        if header.upper() == key:
            return value.strip()
    return None
