"""Manifest discovery following the mcp-manifest.dev resolution algorithm."""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import McpManifest

_TIMEOUT = 10  # seconds


@dataclass
class DiscoveryResult:
    """Result of manifest discovery."""

    manifest: McpManifest | None = None
    source: str = ""
    errors: list[str] = field(default_factory=list)


def _fetch(url: str) -> str:
    """Fetch a URL and return its body text. Raises on failure."""
    req = Request(url, headers={"User-Agent": "mcp-manifest-python/0.1.0"})
    with urlopen(req, timeout=_TIMEOUT) as resp:
        return resp.read().decode("utf-8")


def _looks_like_path(s: str) -> bool:
    """Return True if the string looks like a local file path."""
    if s.startswith(("http://", "https://")):
        return False
    # Absolute or relative paths (Unix or Windows)
    p = Path(s)
    try:
        return p.exists()
    except OSError:
        return False


async def discover(input: str) -> DiscoveryResult:
    """Discover and parse an MCP manifest.

    Resolution order:
    1. Local file path
    2. Direct .json URL
    3. Well-known URL ({base}/.well-known/mcp-manifest.json)
    4. HTML ``<link rel="mcp-manifest">`` tag
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _discover_sync, input)


def _discover_sync(input: str) -> DiscoveryResult:
    """Synchronous implementation of the discovery algorithm."""
    errors: list[str] = []

    # 1. Local file
    if _looks_like_path(input):
        try:
            manifest = McpManifest.from_file(input)
            return DiscoveryResult(manifest=manifest, source=f"file: {input}")
        except Exception as exc:
            return DiscoveryResult(
                source=f"file: {input}", errors=[f"Failed to parse: {exc}"]
            )

    # 2. Direct URL ending in .json
    if input.startswith("http") and input.endswith(".json"):
        try:
            body = _fetch(input)
            manifest = McpManifest._from_dict(json.loads(body))
            return DiscoveryResult(manifest=manifest, source=f"url: {input}")
        except HTTPError as exc:
            errors.append(f"{input} returned {exc.code}")
        except Exception as exc:
            errors.append(f"{input}: {exc}")
        return DiscoveryResult(source=input, errors=errors)

    # 3. Normalize to base URL
    base_url = input
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    base_url = base_url.rstrip("/")

    # 4. Try well-known URL
    well_known = f"{base_url}/.well-known/mcp-manifest.json"
    try:
        body = _fetch(well_known)
        manifest = McpManifest._from_dict(json.loads(body))
        return DiscoveryResult(manifest=manifest, source=f"well-known: {well_known}")
    except HTTPError as exc:
        errors.append(f"well-known: {exc.code}")
    except Exception as exc:
        errors.append(f"well-known: {exc}")

    # 5. Fetch HTML and parse <link rel="mcp-manifest">
    try:
        html = _fetch(base_url)
        match = re.search(
            r'<link[^>]+rel\s*=\s*["\']mcp-manifest["\'][^>]+href\s*=\s*["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        ) or re.search(
            r'<link[^>]+href\s*=\s*["\']([^"\']+)["\'][^>]+rel\s*=\s*["\']mcp-manifest["\']',
            html,
            re.IGNORECASE,
        )

        if match:
            href = match.group(1)
            if href.startswith("/"):
                href = f"{base_url}{href}"
            elif not href.startswith("http"):
                href = f"{base_url}/{href}"

            try:
                body = _fetch(href)
                manifest = McpManifest._from_dict(json.loads(body))
                return DiscoveryResult(
                    manifest=manifest, source=f"link tag: {href}"
                )
            except HTTPError as exc:
                errors.append(f"link tag href {href}: {exc.code}")
            except Exception as exc:
                errors.append(f"link tag href {href}: {exc}")
        else:
            errors.append('no <link rel="mcp-manifest"> found in HTML')
    except Exception as exc:
        errors.append(f"HTML fetch: {exc}")

    # 6. Discovery failed
    return DiscoveryResult(source=base_url, errors=errors)


def check_command(command: str) -> bool:
    """Check whether *command* is available on PATH."""
    return shutil.which(command) is not None
