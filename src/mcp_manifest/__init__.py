"""mcp-manifest -- Discover and parse MCP server manifests."""

from .discover import DiscoveryResult, check_command, discover
from .models import (
    McpManifest,
    McpManifestConfig,
    McpManifestInstall,
    McpManifestServer,
    McpManifestSettingsTemplate,
)
from .validate import ValidationResult, validate

__all__ = [
    "McpManifest",
    "McpManifestConfig",
    "McpManifestInstall",
    "McpManifestServer",
    "McpManifestSettingsTemplate",
    "DiscoveryResult",
    "ValidationResult",
    "discover",
    "validate",
    "check_command",
]
