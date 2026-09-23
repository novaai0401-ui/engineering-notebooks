# Notebook 8 — A remote MCP service you can inspect and test

An MCP server is like a library counter with a standard request form. A client asks what operations exist and calls them using structured arguments. The form does not decide who may enter the library, which shelf belongs to whom, or whether borrowing a book is safe. Those are authentication, authorization and application responsibilities.

## 1. The complete project and its boundaries

The executable project is in `labs/remote-mcp`. `server.py` exposes tools, a resource and a prompt over streamable HTTP. `client.py` makes a real network call. `test_remote.py` launches the server in a separate process and checks allowed access, rejected credentials, permissions, ownership, validation and timeouts. This differs from an in-memory `Client(server)` example: requests cross an actual HTTP boundary.

The project uses opaque bearer tokens supplied through environment variables. The server maps each token to an identity and scopes. Tokens are never accepted from tool arguments. This is a controlled internal-service teaching setup, not a complete OAuth authorization server. FastMCP's [token verification documentation](https://gofastmcp.com/servers/auth/token-verification) distinguishes validation from token issuance and discovery. For public integrations use a compatible authorization server and the appropriate MCP authorization flow; do not invent a login protocol.

## 2. Authentication, scopes, and resource ownership

Authentication asks “who is this?” Authorization asks “may this identity perform this action on this resource?” A scope such as `notes:read` answers part of that second question. It does not permit reading every tenant's notes. Our read tool derives its owner from the verified access token and filters by that owner. A caller cannot submit `owner='bob'` to elevate access.

The server has an Alice reader, an Alice editor and a Bob reader. The reader may read Alice's note but may not write. The editor may write Alice's note. Bob sees Bob's note. Access checks run at the tool boundary as well as shaping discovery. Hiding a tool in the list is useful but is not a substitute for rejecting direct unauthorized calls. See [FastMCP authorization](https://gofastmcp.com/servers/authorization) for the framework hooks used by the project.

**Analogy:** A school badge identifies you. A laboratory permission lets you enter the laboratory. Neither authorizes opening another student's locker. Identity, action permission and resource ownership are three separate checks.

## 3. Request lifecycle and transport behavior

The client connects with credentials, negotiates the capabilities supported by its installed SDK, discovers tools, and sends a typed call. The server authenticates, validates arguments, checks permissions, executes, and returns structured data or a protocol/tool error. Use the SDK rather than manually assuming a particular revision's handshake fields. The current protocol and SDK must be compatible.

Stdio is suitable for a local child process. Streamable HTTP serves network clients and introduces network failures, proxy timeouts and authorization concerns. A transport connection is not a durable business job. If work must survive disconnects, create a job ID and provide status/cancellation operations. A session ID is not a bearer credential. Do not treat possession of a session identifier as authorization.

JSON schemas describe acceptable shapes, but domain checks are still necessary. A string may satisfy a schema and still be too long, refer to an inaccessible object, or request an invalid state transition. Bound input size, output size and execution time. Avoid giving a model a tool that accepts unrestricted filesystem paths or arbitrary commands when a narrow operation will do.

## 4. Timeouts, cancellation, and uncertain outcomes

There are at least three clocks: connection timeout, per-call timeout, and the overall task deadline. The project calls a deliberately slow read-only tool with a shorter client timeout. The test proves that the client stops waiting. It does not prove every remote implementation immediately stops executing when a client disconnects.

If a write times out, its outcome may be unknown. Ask for status using its operation ID or retry with the same idempotency key. Do not automatically send a fresh write with a new key. Bounded exponential backoff with jitter avoids every client retrying at the same instant. Respect the remaining task deadline; an exhausted budget should not create another long retry.

```python
# lab: retry_delay_budget
import random
def retry_delays(attempts, base, cap, remaining, seed=7):
    rng = random.Random(seed)
    delays = []
    for attempt in range(attempts):
        delay = rng.uniform(0, min(cap, base*(2**attempt)))
        if delay > remaining:
            break
        delays.append(delay)
        remaining -= delay
    return delays
delays = retry_delays(5, 0.1, 1.0, 0.5)
assert sum(delays) <= 0.5 and len(delays) <= 5
print('Backoff stays within the waiting budget:', [round(x, 3) for x in delays])
```

This example budgets delays only. A real retry loop subtracts operation time too and retries only classified transient failures. Validation errors, missing permission and malformed requests generally do not improve through repetition.

## 5. Errors that help without leaking secrets

A connection failure means the peer was not reached. An authentication error means credentials were absent or unacceptable. Authorization denies an action. Argument validation rejects a malformed request. A tool error reports execution failure. Keep those categories separate so the caller can choose an appropriate response.

Return a stable public error and a correlation ID. Detailed stack traces belong in protected logs, with tokens and sensitive arguments redacted. Do not return another user's resource name merely to explain a denial. The note tool treats ownership as server-side state; its inputs never contain a token.

For business errors, decide whether the protocol's error channel or a documented result union fits the SDK and clients. Never return a success-shaped object containing an unnoticed error string. Clients should inspect the error flag or exception before trusting structured output.

## 6. Run the project

From the notebook root, use the environment installed for the notebooks:

```powershell
.\.venv\Scripts\python labs/remote-mcp/test_remote.py
```

The test creates temporary random tokens, runs on loopback, cleans up its server process, and writes `labs/remote-mcp/test-report.json`. To run manually, set three distinct random environment values named `MCP_ALICE_READ_TOKEN`, `MCP_ALICE_WRITE_TOKEN`, and `MCP_BOB_READ_TOKEN`, then run `server.py`. Set `MCP_CLIENT_TOKEN` to the reader token and run `client.py` in another terminal. Do not paste secrets into a notebook output or commit them.

The server's in-memory notes deliberately reset on restart. The project demonstrates remote MCP transport and access control; it does not claim durable note storage. The Study Coach project separately demonstrates durable storage. Replacing the dictionary with a repository is an exercise in separating protocol code from persistence.

## 7. Deployment and operation

The project includes a Dockerfile and deployment instructions. A container is a process package, not a security policy. Supply secrets at runtime, run as a non-root user, publish only intended ports, and terminate TLS at a trusted reverse proxy for access beyond loopback. Configure allowed hosts/origins for the chosen SDK and proxy. Keep proxy buffering and timeouts compatible with streaming.

Protect logs and metrics, cap concurrent calls, and use a bounded queue for expensive tools. Expose a separate health endpoint if your deployment needs it; health should not execute expensive tools. Rolling upgrades must keep protocol and application schemas compatible while old requests finish. Rotate tokens and revoke old credentials. Public OAuth deployments need issuer/audience/expiry validation, key rotation and discovery beyond this static-token teaching profile.

Docker packaging is supplied for reproducibility, but container execution is only marked tested if the validation report records a Docker run. Local subprocess network tests are not the same as a TLS or cloud deployment test.

## 8. Interview round and answers

**Question, 10 points:** A reader sees only `read_note` during discovery but guesses the name `write_note`. Is the server safe? **Answer:** Only if authorization also rejects direct invocation (3). Tool discovery is not an enforcement boundary (2). Identity comes from validated credentials, not model-supplied arguments (2). Resource ownership remains necessary even with write scope (2). Test both listed and guessed calls (1).

**Debugging:** A write timed out and the retry created a duplicate. Find the missing contract. **Answer:** The server and client need a stable operation key, payload binding and durable deduplication; timeout does not establish non-execution.

**Design alternative:** If only your own backend calls one fixed function, ordinary HTTP may be simpler than MCP. Choose MCP when its standardized tool/resource/prompt interface and client ecosystem solve a real interoperability need. A protocol should reduce integration work, not become an extra layer without a purpose.
