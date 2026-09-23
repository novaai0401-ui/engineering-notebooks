import asyncio
import os
from fastmcp import Client
async def main():
    async with Client(os.getenv('MCP_URL','http://127.0.0.1:8093/mcp'),auth=os.environ['MCP_CLIENT_TOKEN'],timeout=5) as client:
        result=await client.call_tool('read_note',{})
        print(result.data)
if __name__=='__main__': asyncio.run(main())
