"""Client IP resolution behind trusted proxies (enterprise hardening).

We only trust Forwarded/X-Forwarded-For when the immediate peer IP is within
an allowlist of trusted proxy CIDRs.
"""

from __future__ import annotations

import ipaddress
from typing import Iterable

from fastapi import Request


def _parse_cidrs(raw: str) -> list[ipaddress._BaseNetwork]:  # type: ignore[name-defined]
    cidrs: list[ipaddress._BaseNetwork] = []  # type: ignore[name-defined]
    for part in (raw or "").split(","):
        p = part.strip()
        if not p:
            continue
        try:
            cidrs.append(ipaddress.ip_network(p, strict=False))
        except Exception:
            continue
    return cidrs


def _ip_in_any(ip: str | None, nets: Iterable[ipaddress._BaseNetwork]) -> bool:  # type: ignore[name-defined]
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except Exception:
        return False
    for n in nets:
        if addr in n:
            return True
    return False


def _parse_forwarded(forwarded: str) -> list[str]:
    # Forwarded: for=1.2.3.4, for=5.6.7.8; proto=https; by=...
    res: list[str] = []
    for item in (forwarded or "").split(","):
        s = item.strip()
        if not s:
            continue
        parts = [p.strip() for p in s.split(";")]
        for p in parts:
            if p.lower().startswith("for="):
                v = p[4:].strip().strip('"')
                # may include IPv6 in brackets
                v = v.strip("[]")
                # may include port
                if ":" in v and v.count(":") == 1 and v.split(":")[1].isdigit():
                    v = v.split(":")[0]
                res.append(v)
    return res


def resolve_client_ip(
    request: Request,
    *,
    trusted_proxy_cidrs: str,
    allow_forwarded: bool = True,
) -> str | None:
    """Resolve the real client IP when behind trusted proxies."""
    peer_ip = getattr(getattr(request, "client", None), "host", None)
    if not allow_forwarded:
        return peer_ip

    trusted = _parse_cidrs(trusted_proxy_cidrs)
    if not _ip_in_any(peer_ip, trusted):
        return peer_ip

    # Prefer RFC 7239 Forwarded
    fwd = request.headers.get("forwarded")
    if fwd:
        ips = _parse_forwarded(fwd)
        if ips:
            return ips[0]

    xff = request.headers.get("x-forwarded-for")
    if xff:
        # XFF: client, proxy1, proxy2...
        first = xff.split(",")[0].strip()
        if first:
            return first
    return peer_ip

