"""Dataclass models for the mcp-manifest.dev spec (v1.0).

Security-related fields are documented inline; see the spec's THREAT-MODEL.md
for the rationale behind each field.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class McpManifestOptionsFrom:
    """Dynamically resolve available config values from a local file."""
    file: str = ""
    """Path to a local JSON file. ~ is expanded to the user's home directory."""
    path: str = ""
    """JSONPath expression to extract values from the file."""


@dataclass
class McpManifestConfig:
    """A configuration parameter the server accepts."""

    key: str
    description: str
    type: str  # string | boolean | number | path | url | secret
    required: bool = False
    default: Any = None
    env_var: str | None = None
    arg: str | None = None
    prompt: str | None = None
    options: list[str] = field(default_factory=list)
    options_from: McpManifestOptionsFrom | None = None
    secret_target: str | None = None
    """Intended recipient origin for secrets (e.g., 'api.openai.com'). REQUIRED when type='secret'. (T3)"""
    secret_scope_url: str | None = None
    """URL pattern this secret may be sent to. (T3)"""


@dataclass
class McpManifestInstall:
    """An installation method for the server."""

    method: str  # dotnet-tool | npm | pip | cargo | gem | prebuilt-binary | docker
    package: str
    command: str
    registry: str | None = None
    """Explicit registry origin URL. RECOMMENDED for non-default registries. (T2)"""
    checksum: str | None = None
    """SHA-256 checksum 'sha256:HEX'. REQUIRED when method='prebuilt-binary'. (T2)"""
    priority: int = 0


@dataclass
class McpManifestServer:
    """Server metadata."""

    name: str
    display_name: str
    description: str
    version: str
    author: str | None = None
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    keywords: list[str] = field(default_factory=list)
    icon: str | None = None


@dataclass
class McpManifestSettingsTemplate:
    """Pre-built template for client MCP server configuration."""

    command: str | None = None
    args: list[str] = field(default_factory=list)


@dataclass
class McpManifestSignature:
    """Cryptographic signature over the canonicalized manifest. (T1)

    The signed payload is the manifest JSON with the `signature` field removed,
    canonicalized via RFC 8785 (JCS), then signed with Ed25519.
    """
    alg: str = "Ed25519"
    """Currently only 'Ed25519' is defined."""
    key_id: str = ""
    """Opaque identifier for the publisher's signing key."""
    value: str = ""
    """Base64url-encoded signature (no padding)."""


@dataclass
class McpManifest:
    """Top-level MCP manifest object (spec v1.0)."""

    version: str
    server: McpManifestServer
    install: list[McpManifestInstall]
    transport: str  # stdio | sse | streamable-http
    endpoint: str | None = None
    config: list[McpManifestConfig] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    settings_template: McpManifestSettingsTemplate | None = None
    update_policy: str | None = None
    """How clients should handle updates: auto | manual | ask. Default 'manual'. (T4)"""
    changelog_url: str | None = None
    """URL to a human-readable changelog displayed during update prompts. (T4)"""
    signature: McpManifestSignature | None = None
    """Cryptographic publisher signature. (T1)"""
    extensions: dict[str, Any] = field(default_factory=dict)
    """Vendor extensions; keys MUST start with 'x-'. (T5)"""

    # --- Construction helpers ------------------------------------------------

    @classmethod
    def from_json(cls, json_str: str) -> McpManifest:
        """Parse a manifest from a JSON string."""
        data = json.loads(json_str)
        return cls._from_dict(data)

    @classmethod
    def from_file(cls, path: str | Path) -> McpManifest:
        """Parse a manifest from a local file (synchronous)."""
        text = Path(path).read_text(encoding="utf-8")
        return cls.from_json(text)

    # --- Internal ------------------------------------------------------------

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> McpManifest:
        server_data = data["server"]
        server = McpManifestServer(
            name=server_data["name"],
            display_name=server_data["displayName"],
            description=server_data["description"],
            version=server_data["version"],
            author=server_data.get("author"),
            homepage=server_data.get("homepage"),
            repository=server_data.get("repository"),
            license=server_data.get("license"),
            keywords=server_data.get("keywords", []),
            icon=server_data.get("icon"),
        )

        install = [
            McpManifestInstall(
                method=i["method"],
                package=i["package"],
                command=i["command"],
                registry=i.get("registry") or i.get("source"),  # accept legacy "source" for backward compat
                checksum=i.get("checksum"),
                priority=i.get("priority", 0),
            )
            for i in data["install"]
        ]

        config = [
            McpManifestConfig(
                key=c["key"],
                description=c["description"],
                type=c["type"],
                required=c.get("required", False),
                default=c.get("default"),
                env_var=c.get("env_var"),
                arg=c.get("arg"),
                prompt=c.get("prompt"),
                options=c.get("options", []),
                options_from=McpManifestOptionsFrom(
                    file=c["options_from"]["file"],
                    path=c["options_from"]["path"],
                ) if c.get("options_from") else None,
                secret_target=c.get("secret_target"),
                secret_scope_url=c.get("secret_scope_url"),
            )
            for c in data.get("config", [])
        ]

        settings_template = None
        if "settings_template" in data:
            st = data["settings_template"]
            settings_template = McpManifestSettingsTemplate(
                command=st.get("command"),
                args=st.get("args", []),
            )

        signature = None
        if "signature" in data:
            sig = data["signature"]
            signature = McpManifestSignature(
                alg=sig.get("alg", "Ed25519"),
                key_id=sig.get("key_id", ""),
                value=sig.get("value", ""),
            )

        return cls(
            version=data["version"],
            server=server,
            install=install,
            transport=data["transport"],
            endpoint=data.get("endpoint"),
            config=config,
            scopes=data.get("scopes", []),
            settings_template=settings_template,
            update_policy=data.get("update_policy"),
            changelog_url=data.get("changelog_url"),
            signature=signature,
            extensions=data.get("extensions", {}),
        )
