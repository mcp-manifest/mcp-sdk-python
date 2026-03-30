"""Manifest validation beyond JSON parsing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .models import McpManifest

_VALID_TRANSPORTS = {"stdio", "sse", "streamable-http"}
_VALID_CONFIG_TYPES = {"string", "boolean", "number", "path", "url", "secret"}
_VALID_METHODS = {"dotnet-tool", "npm", "pip", "cargo", "binary", "docker"}
_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")


@dataclass
class ValidationResult:
    """Result of manifest validation."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)


def validate(manifest: McpManifest) -> ValidationResult:
    """Validate a parsed manifest for structural and semantic correctness.

    Checks performed:
    - Required fields present and non-empty
    - Transport/endpoint consistency
    - Duplicate config keys
    - settings_template variable references match config keys
    """
    errors: list[str] = []

    # --- Required top-level fields -------------------------------------------
    if not manifest.version:
        errors.append("version is required")

    if not manifest.transport:
        errors.append("transport is required")
    elif manifest.transport not in _VALID_TRANSPORTS:
        errors.append(
            f'transport "{manifest.transport}" is not valid; '
            f"expected one of: {', '.join(sorted(_VALID_TRANSPORTS))}"
        )

    # --- Server metadata -----------------------------------------------------
    srv = manifest.server
    if not srv.name:
        errors.append("server.name is required")
    elif not _NAME_PATTERN.match(srv.name):
        errors.append(
            f'server.name "{srv.name}" must be lowercase with hyphens '
            f"(pattern: {_NAME_PATTERN.pattern})"
        )
    if not srv.display_name:
        errors.append("server.displayName is required")
    if not srv.description:
        errors.append("server.description is required")
    if not srv.version:
        errors.append("server.version is required")

    # --- Install entries -----------------------------------------------------
    if not manifest.install:
        errors.append("at least one install entry is required")
    else:
        for i, inst in enumerate(manifest.install):
            prefix = f"install[{i}]"
            if not inst.method:
                errors.append(f"{prefix}.method is required")
            elif inst.method not in _VALID_METHODS:
                errors.append(
                    f'{prefix}.method "{inst.method}" is not valid; '
                    f"expected one of: {', '.join(sorted(_VALID_METHODS))}"
                )
            if not inst.package:
                errors.append(f"{prefix}.package is required")
            if not inst.command:
                errors.append(f"{prefix}.command is required")

    # --- Transport / endpoint ------------------------------------------------
    if manifest.transport in ("sse", "streamable-http"):
        if not manifest.endpoint:
            errors.append(
                f'transport "{manifest.transport}" requires an "endpoint" URL'
            )

    # --- Duplicate config keys -----------------------------------------------
    if manifest.config:
        keys = [c.key for c in manifest.config]
        seen: set[str] = set()
        dupes: set[str] = set()
        for k in keys:
            if k in seen:
                dupes.add(k)
            seen.add(k)
        if dupes:
            errors.append(f"duplicate config keys: {', '.join(sorted(dupes))}")

        for j, cfg in enumerate(manifest.config):
            if cfg.type not in _VALID_CONFIG_TYPES:
                errors.append(
                    f'config[{j}].type "{cfg.type}" is not valid; '
                    f"expected one of: {', '.join(sorted(_VALID_CONFIG_TYPES))}"
                )

    # --- settings_template variable references -------------------------------
    if manifest.settings_template is not None:
        template_str = json.dumps(
            {
                "command": manifest.settings_template.command,
                "args": manifest.settings_template.args,
            }
        )
        var_refs = re.findall(r"\$\{([^}]+)\}", template_str)
        config_keys = {c.key for c in manifest.config}
        for ref in var_refs:
            if ref not in config_keys:
                errors.append(
                    f'settings_template references "${{{ref}}}" '
                    f'but no config entry has key "{ref}"'
                )

    return ValidationResult(valid=len(errors) == 0, errors=errors)
