# MCPDOC Examples

This directory contains example implementations and usage patterns for MCPDOC.

## Examples

### langgraph.py - Simple MCP Server

A minimal example showing how to create a basic MCP server for serving LangGraph documentation.

**Features:**
- Single documentation source (LangGraph)
- Hardcoded domain validation
- Simple `get_docs` tool
- Direct execution support

**Usage:**

```bash
# Run directly
python examples/langgraph.py

# Or with uvx
uvx --from mcp python examples/langgraph.py
```

**Code Overview:**

```python
from mcp.server.fastmcp import FastMCP

server = FastMCP(name="llms-txt")

@server.tool()
async def get_docs(url: str = "overview") -> str:
    """Get langgraph docs."""
    # Fetch and return documentation
    pass

if __name__ == "__main__":
    server.run(transport="stdio")
```

This example is useful for:
- Understanding the basics of MCP servers
- Creating custom documentation servers
- Learning the FastMCP API

## Creating Your Own Example

Want to add your own example? Here's a template:

```python
"""Description of what this example demonstrates."""

import httpx
from markdownify import markdownify
from mcp.server.fastmcp import FastMCP

server = FastMCP(name="your-server-name")

# Your configuration
ALLOWED_DOMAIN = "https://your-domain.com/"

@server.tool()
async def your_tool(param: str) -> str:
    """Description of your tool.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
    """
    # Your implementation
    pass

if __name__ == "__main__":
    server.run(transport="stdio")
```

## Using Examples as Templates

You can use these examples as starting points for your own MCP servers:

1. Copy an example file
2. Modify the documentation source and domain
3. Customize the tools and functionality
4. Test locally with MCP Inspector
5. Deploy to your MCP host (Cursor, Claude Desktop, etc.)

## Testing Examples

Test examples with the MCP Inspector:

```bash
# Start your example server
python examples/your_example.py

# In another terminal, run MCP Inspector
npx @modelcontextprotocol/inspector
```

## More Complex Examples

For more sophisticated usage patterns, see the main `mcpdoc` implementation:

- **Multiple documentation sources**: See `mcpdoc/main.py`
- **CLI interface**: See `mcpdoc/cli.py`
- **Configuration files**: See `sample_config.yaml` and `sample_config.json`

## Contributing Examples

Have a useful example? We'd love to include it! See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

Good examples to add:
- Custom documentation sources
- Different authentication methods
- Caching strategies
- Error handling patterns
- Integration with specific IDEs or tools

