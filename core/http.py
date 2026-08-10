"""Shared httpx client factory with safe proxy handling.

httpx's ``trust_env=True`` eagerly parses every proxy-related env var
(including ``ALL_PROXY``) and raises if one of them uses a scheme httpx
can't handle without an extra dependency (e.g. ``socks://`` without the
``httpx[socks]`` extra). Some environments block direct outbound requests
to certain hosts (e.g. Cloudflare WAF flags datacenter/sandbox IPs), so
requests must go through the local ``HTTP(S)_PROXY`` when one is set.
"""

import os
import httpx


def new_client(timeout: int) -> httpx.AsyncClient:
    proxy = (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
    )
    if proxy and not proxy.startswith(("http://", "https://")):
        proxy = None
    return httpx.AsyncClient(timeout=timeout, trust_env=False, proxy=proxy)
