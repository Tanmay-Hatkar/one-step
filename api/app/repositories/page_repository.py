"""Fetch a public web page a user pasted a link to — and nothing else.

A pasted link is untrusted input that makes the server open a connection, so every hop
is checked: http(s) on the default port only, the host must resolve to public addresses,
the connection is pinned to the address that was checked, redirects are followed by hand
(and re-checked), and the body is capped.
"""

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from urllib.parse import SplitResult, urljoin, urlsplit

import httpx

logger = logging.getLogger(__name__)

REDIRECTS = frozenset({301, 302, 303, 307, 308})
DEFAULT_PORTS = {"http": 80, "https": 443}
READABLE_TYPES = ("text/html", "application/xhtml+xml", "text/plain")


class PageUnreadable(RuntimeError):
    """The link couldn't be opened or isn't a page we're willing to read."""


class LinkNotSupported(PageUnreadable):
    """A site that needs a login or is video only (Instagram, TikTok, YouTube…)."""


@dataclass(frozen=True)
class _Target:
    """One checked hop: the URL as written and the public address to connect to."""

    url: SplitResult
    host: str
    address: str


class PageRepository:
    """Reads the HTML of a public page."""

    def __init__(
        self,
        timeout: float,
        max_bytes: int,
        max_redirects: int,
        user_agent: str,
        unreadable_hosts: list[str],
    ) -> None:
        """Args: timeout seconds, max_bytes read per page, max_redirects, user_agent,
        unreadable_hosts (sites refused up front with a clearer error)."""
        self._timeout = timeout
        self._max_bytes = max_bytes
        self._max_redirects = max_redirects
        self._user_agent = user_agent
        self._unreadable = tuple(unreadable_hosts)

    async def read(self, url: str) -> str:
        """Return the page's HTML (at most `max_bytes` of it).

        Args:
            url: An http(s) link.

        Returns:
            The decoded body.

        Raises:
            LinkNotSupported: For sites that can't be read without a login.
            PageUnreadable: For anything else that can't or shouldn't be fetched.
        """
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, follow_redirects=False, trust_env=False
            ) as client:
                for _ in range(self._max_redirects + 1):
                    target = await self._check(url)
                    status, location, body = await self._get(client, target)
                    if status in REDIRECTS and location:
                        url = urljoin(url, location)
                        continue
                    if status != httpx.codes.OK:
                        raise PageUnreadable(f"HTTP {status}")
                    return body
        except httpx.HTTPError as exc:
            logger.info("Page fetch failed: %s", type(exc).__name__)
            raise PageUnreadable("fetch failed") from exc
        raise PageUnreadable("too many redirects")

    async def _check(self, url: str) -> _Target:
        """Validate one hop and resolve it to a public address."""
        try:
            parts = urlsplit(url)
            port = parts.port
        except ValueError as exc:
            raise PageUnreadable("bad link") from exc
        host = (parts.hostname or "").lower()
        if parts.scheme not in DEFAULT_PORTS or not host or parts.username or parts.password:
            raise PageUnreadable("not a plain web link")
        if port not in (None, DEFAULT_PORTS[parts.scheme]):
            raise PageUnreadable("unusual port")
        if any(host == h or host.endswith("." + h) for h in self._unreadable):
            raise LinkNotSupported(host)
        return _Target(parts, host, await self._public_address(host, DEFAULT_PORTS[parts.scheme]))

    @staticmethod
    async def _public_address(host: str, port: int) -> str:
        """Resolve `host`; every address must be public. Returns the first."""
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(
                host, port, type=socket.SOCK_STREAM
            )
        except (OSError, UnicodeError) as exc:
            raise PageUnreadable("host not found") from exc
        addresses = [info[4][0] for info in infos]
        if not addresses or not all(ipaddress.ip_address(a).is_global for a in addresses):
            raise PageUnreadable("not a public address")
        return addresses[0]

    async def _get(self, client: httpx.AsyncClient, target: _Target) -> tuple[int, str, str]:
        """GET one hop, connecting to the checked address. Returns (status, Location, body)."""
        literal = f"[{target.address}]" if ":" in target.address else target.address
        path = target.url.path or "/"
        query = f"?{target.url.query}" if target.url.query else ""
        async with client.stream(
            "GET",
            f"{target.url.scheme}://{literal}{path}{query}",
            headers={
                "Host": target.host,
                "User-Agent": self._user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en",
            },
            # TLS is verified against the real hostname even though we dial the address.
            extensions={"sni_hostname": target.host},
        ) as response:
            location = response.headers.get("location", "")
            if response.status_code != httpx.codes.OK:
                return response.status_code, location, ""
            kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if kind not in READABLE_TYPES:
                raise PageUnreadable(f"not a web page ({kind or 'unknown type'})")
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                chunks.append(chunk)
                size += len(chunk)
                if size >= self._max_bytes:
                    break
            raw = b"".join(chunks)[: self._max_bytes]
            return (
                response.status_code,
                location,
                raw.decode(response.encoding or "utf-8", "replace"),
            )
