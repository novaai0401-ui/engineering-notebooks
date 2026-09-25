# Real NGINX load-balancing lab

See Notebook 32 for the full explanation. This test uses actual NGINX and two Python subprocess backends. It needs Python 3 and nginx on Linux. It binds only ephemeral loopback ports, generates bearer credentials and does not modify a public proxy configuration.

On Windows, from the library root with the isolated WSL lab prepared:

```shell
wsl -d EngineeringNotebookLab-13e66a98 --exec /sbin/apk add --no-cache nginx python3
python labs/run_linux_lab.py load-balancing
```

On Linux: `python3 labs/load-balancing/test_nginx.py`.

The report checks round robin, weights, authentication, forwarded-header sanitization, incremental SSE, no replay of an effect-producing POST, backend death and total backend unavailability. A handshake between test client and backend controls the second SSE event, so the streaming check tests first-event delivery before completion rather than relying on a fragile elapsed-time threshold.

Temporary configuration/logs use a private Linux temporary directory. Processes stop in finally cleanup. The sample backend is a teaching HTTP server, not a production application. The test does not certify TLS, WebSocket proxying, L4 balancing, active health checks, cloud infrastructure or independent-host failure. Separate notebook cells teach other algorithms without pretending to be production proxies.

After completing all Windows Linux-lab tests, release the VM with `wsl --terminate EngineeringNotebookLab-13e66a98`. Do not stop it while a test is running.
