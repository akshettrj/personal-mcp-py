from src.server import MCP_SERVER
from src.tools import *

def main():
    MCP_SERVER.run(transport="stdio")


if __name__ == "__main__":
    main()
