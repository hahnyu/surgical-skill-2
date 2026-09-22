"""Read selected members of large public ZIP deposits through HTTP ranges."""

from __future__ import annotations

import io
import urllib.error
import urllib.request
import zipfile


class HTTPRangeFile(io.RawIOBase):
    """Seekable read-only HTTP object with a bounded sequential cache.

    The server must honor Range requests. A full 200 response is rejected to
    prevent accidental downloads of the 400 GB PatCut deposit.
    """

    def __init__(self, url: str, size: int, cache_bytes: int = 16 * 1024 * 1024):
        self.url = url
        self.size = int(size)
        self.cache_bytes = int(cache_bytes)
        self._position = 0
        self._cache_start = 0
        self._cache = b""

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            position = offset
        elif whence == io.SEEK_CUR:
            position = self._position + offset
        elif whence == io.SEEK_END:
            position = self.size + offset
        else:
            raise ValueError(f"invalid whence: {whence}")
        if position < 0:
            raise ValueError("negative seek position")
        self._position = min(position, self.size)
        return self._position

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = self.size - self._position
        if size == 0 or self._position >= self.size:
            return b""
        size = min(size, self.size - self._position)
        cache_end = self._cache_start + len(self._cache)
        if self._cache_start <= self._position and self._position + size <= cache_end:
            start = self._position - self._cache_start
            data = self._cache[start : start + size]
            self._position += len(data)
            return data

        request_end = min(self.size - 1, self._position + max(size, self.cache_bytes) - 1)
        for attempt in range(5):
            request = urllib.request.Request(
                self.url,
                headers={
                    "Range": f"bytes={self._position}-{request_end}",
                    "User-Agent": "surgical-skill-phase2/0.1",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    status = getattr(response, "status", None)
                    content_range = response.headers.get("Content-Range")
                    if status != 206 and not content_range:
                        raise OSError("server ignored Range request; refusing full-object download")
                    downloaded = response.read()
                    self.url = response.geturl()
                break
            except (TimeoutError, ConnectionError, urllib.error.URLError):
                if attempt == 4:
                    raise
        self._cache = downloaded
        self._cache_start = self._position
        data = self._cache[:size]
        self._position += len(data)
        return data


def open_remote_zip(url: str, size: int) -> zipfile.ZipFile:
    """Open a central-directory-backed ZIP without downloading the full object."""
    return zipfile.ZipFile(HTTPRangeFile(url, size), mode="r")
