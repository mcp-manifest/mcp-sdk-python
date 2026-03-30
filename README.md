[![MCP Manifest](https://mcp-manifest.dev/media/mcp-manifest-badge-light.svg)](https://mcp-manifest.dev)

# mcp-manifest

Python SDK for the [mcp-manifest.dev](https://mcp-manifest.dev) spec. Discover, parse, and validate MCP server manifests with zero runtime dependencies.

## Install

```bash
pip install mcp-manifest
```

## Usage

### Parse a local manifest

```python
from mcp_manifest import McpManifest

manifest = McpManifest.from_file("mcp-manifest.json")
print(manifest.server.display_name)
```

### Discover a manifest from a domain

```python
import asyncio
from mcp_manifest import discover

result = asyncio.run(discover("ironlicensing.com"))
if result.manifest:
    print(f"Found via {result.source}")
    print(result.manifest.server.description)
else:
    print("Discovery failed:", result.errors)
```

### Validate a manifest

```python
from mcp_manifest import McpManifest, validate

manifest = McpManifest.from_file("mcp-manifest.json")
result = validate(manifest)
if result.valid:
    print("Manifest is valid")
else:
    for error in result.errors:
        print(f"  - {error}")
```

### Check if a command is installed

```python
from mcp_manifest import check_command

if check_command("ironlicensing-mcp"):
    print("Ready to use")
```

### Async discovery

```python
import asyncio
from mcp_manifest import discover

async def main():
    result = await discover("ironlicensing.com")
    if result.manifest:
        for install in result.manifest.install:
            print(f"{install.method}: {install.package}")

asyncio.run(main())
```

## License

CC0 1.0 -- Public domain.
