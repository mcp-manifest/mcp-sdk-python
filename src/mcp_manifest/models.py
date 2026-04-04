"""Dataclass models for the mcp-manifest.dev spec (v0.1)."""

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


@dataclass
class McpManifestInstall:
    """An installation method for the server."""

    method: str  # dotnet-tool | npm | pip | cargo | binary | docker
    package: str
    command: str
    source: str | None = None
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
class McpManifest:
    """Top-level MCP manifest object."""

    version: str
    server: McpManifestServer
    install: list[McpManifestInstall]
    transport: str  # stdio | sse | streamable-http
    endpoint: str | None = None
    config: list[McpManifestConfig] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    settings_template: McpManifestSettingsTemplate | None = None

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
                source=i.get("source"),
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

        return cls(
            version=data["version"],
            server=server,
            install=install,
            transport=data["transport"],
            endpoint=data.get("endpoint"),
            config=config,
            scopes=data.get("scopes", []),
            settings_template=settings_template,
        )
