import asyncio
import os
from fastmcp import FastMCP
from fastmcp.server.auth import require_scopes
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.exceptions import ToolError

tokens = {
    os.environ['MCP_ALICE_READ_TOKEN']: {'client_id': 'alice', 'scopes': ['notes:read']},
    os.environ['MCP_ALICE_WRITE_TOKEN']: {'client_id': 'alice', 'scopes': ['notes:read','notes:write']},
    os.environ['MCP_BOB_READ_TOKEN']: {'client_id': 'bob', 'scopes': ['notes:read']},
}
if len(tokens) != 3 or any(len(token)<24 for token in tokens):
    raise ValueError('Supply three distinct random tokens of at least 24 characters')
server = FastMCP('Scoped study notes', auth=StaticTokenVerifier(tokens=tokens))
notes={'alice':'Alice studies durable agents.', 'bob':'Bob studies database isolation.'}

def owner():
    token=get_access_token()
    if token is None or token.client_id not in notes:
        raise ToolError('identity not authorized')
    return token.client_id

@server.tool(auth=require_scopes('notes:read'))
def read_note() -> dict:
    """Read only the authenticated learner's note."""
    identity=owner()
    return {'owner':identity,'text':notes[identity]}

@server.tool(auth=require_scopes('notes:write'))
def write_note(text: str) -> dict:
    """Replace your own short study note."""
    if not text.strip() or len(text)>200:
        raise ToolError('note must contain 1 to 200 characters')
    identity=owner();notes[identity]=text
    return {'owner':identity,'saved':True}

@server.tool(auth=require_scopes('notes:read'))
async def slow_read(seconds: float=1.0) -> dict:
    """A bounded read-only delay for timeout experiments."""
    if not 0<=seconds<=2:
        raise ToolError('delay must be between zero and two seconds')
    await asyncio.sleep(seconds)
    return {'owner':owner()}

@server.resource('study://principles',auth=require_scopes('notes:read'))
def principles() -> str:
    return 'Authenticate first. Check action scope. Enforce ownership. Bound work.'

@server.prompt(auth=require_scopes('notes:read'))
def explain(topic: str) -> str:
    return f'Explain this learner-provided topic with an example: {topic[:200]}'

if __name__=='__main__':
    server.run(transport='http',host=os.getenv('MCP_HOST','127.0.0.1'),port=int(os.getenv('MCP_PORT','8093')),show_banner=False)
