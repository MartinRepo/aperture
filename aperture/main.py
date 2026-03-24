"""Aperture — personal knowledge harness, exposed as an MCP server."""

from aperture.mcp_server import mcp


def cli() -> None:
    """Run the Aperture MCP server."""
    mcp.run()


if __name__ == "__main__":
    cli()
