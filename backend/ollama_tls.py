"""The chatbot's Ollama proxy: no certificate check, and http -> https redirects keep the POST.

The proxy (IIS, reached by IP) redirects http:// to https://, and its certificate names a
domain, so an IP never matches it. Out of the box that fails every LLM call twice over:
httpx/requests refuse the certificate, and a 301 turns the POST into a GET (Ollama answers
405).

install() adds, to every httpx client created in this process, a transport for the proxy's
host ONLY (the hosts in OLLAMA_BASE_URL, TRANSLATION_BASE_URL and the other *TRANSLATION*
BASE_URL settings). That transport
  - does not check the HTTPS certificate: the connection is still encrypted, but the server
    is not authenticated -- acceptable on a network you trust;
  - on an http -> https redirect to the SAME host, repeats the request over https with the
    same method and body, then sends later requests to https directly.
Every other host keeps normal certificate checking. Set LLM_VERIFY_SSL=true to turn all of
this off. No proxy host configured = no change at all.
"""
from __future__ import annotations

import functools
import os
from urllib.parse import urlparse

import httpx

_REDIRECTS = (301, 302, 303, 307, 308)
_hosts: set[str] = set()
_upgraded: set[str] = set()          # hosts known to redirect http -> https
_installed = False


def _proxy_hosts() -> set[str]:
    hosts: set[str] = set()
    for key, value in os.environ.items():
        if key.endswith("BASE_URL") and ("OLLAMA" in key or "TRANSLATION" in key) and value.strip():
            host = urlparse(value.strip()).hostname
            if host:
                hosts.add(host.lower())
    return hosts


def _default_http_port(url: httpx.URL) -> bool:
    return url.scheme == "http" and url.port in (None, 80)


def _go_https_if_known(request: httpx.Request) -> None:
    if request.url.host.lower() in _upgraded and _default_http_port(request.url):
        request.url = request.url.copy_with(scheme="https", port=None)


def _https_target(request: httpx.Request, response: httpx.Response):
    """The https URL to repeat the request at, or None when this is not an
    http -> https redirect on the same host (or the body cannot be repeated)."""
    location = response.headers.get("location")
    if response.status_code not in _REDIRECTS or not location or not _default_http_port(request.url):
        return None
    target = request.url.join(location)
    if target.scheme != "https" or target.host.lower() != request.url.host.lower():
        return None
    try:
        request.content
    except httpx.RequestNotRead:
        return None                  # streamed body: cannot be sent twice
    return target


def _repeat(request: httpx.Request, target) -> httpx.Request:
    _upgraded.add(request.url.host.lower())
    return httpx.Request(
        request.method, target, headers=request.headers,
        content=request.content, extensions=request.extensions,
    )


class _SyncTransport(httpx.HTTPTransport):
    def handle_request(self, request):
        _go_https_if_known(request)
        response = super().handle_request(request)
        target = _https_target(request, response)
        if target is None:
            return response
        response.close()
        return super().handle_request(_repeat(request, target))


class _AsyncTransport(httpx.AsyncHTTPTransport):
    async def handle_async_request(self, request):
        _go_https_if_known(request)
        response = await super().handle_async_request(request)
        target = _https_target(request, response)
        if target is None:
            return response
        await response.aclose()
        return await super().handle_async_request(_repeat(request, target))


def _mounts(existing, transport_cls):
    mounts = dict(existing or {})
    for host in _hosts:
        for scheme in ("http", "https"):
            mounts.setdefault(f"{scheme}://{host}", transport_cls(verify=False))
    return mounts


def install() -> set[str]:
    """Idempotent. Returns the proxy hosts that were set up (empty = nothing changed)."""
    global _installed
    if _installed or os.environ.get("LLM_VERIFY_SSL", "").strip().lower() in ("1", "true", "yes", "on"):
        return set(_hosts)
    hosts = _proxy_hosts()
    if not hosts:
        return set()
    _hosts.update(hosts)

    sync_init, async_init = httpx.Client.__init__, httpx.AsyncClient.__init__

    @functools.wraps(sync_init)
    def client_init(self, *args, **kwargs):
        kwargs["mounts"] = _mounts(kwargs.get("mounts"), _SyncTransport)
        sync_init(self, *args, **kwargs)

    @functools.wraps(async_init)
    def async_client_init(self, *args, **kwargs):
        kwargs["mounts"] = _mounts(kwargs.get("mounts"), _AsyncTransport)
        async_init(self, *args, **kwargs)

    httpx.Client.__init__ = client_init
    httpx.AsyncClient.__init__ = async_client_init
    _installed = True
    return set(_hosts)


def describe() -> str:
    if not _installed:
        return "[ollama_tls] off (no proxy host configured, or LLM_VERIFY_SSL=true)"
    return ("[ollama_tls] certificate NOT checked and http->https redirects keep the POST for: "
            + ", ".join(sorted(_hosts)))
