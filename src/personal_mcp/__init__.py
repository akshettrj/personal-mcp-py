from fastmcp import FastMCP

MCP_SERVER = FastMCP("personal-mcp-py")

from personal_mcp.tools import *

def main():
    MCP_SERVER.run(transport="stdio")
