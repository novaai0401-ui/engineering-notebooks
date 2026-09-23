# 24 — Kubernetes: a caretaker for running applications

## 1. The school caretaker story

Docker packages an application. Kubernetes manages desired running state across machines. Imagine asking a caretaker to keep two classrooms open: if one closes, the caretaker arranges a replacement. That does not restore a child's lost notebook unless the notebook was stored safely. Replacing a Pod is not database recovery.

A cluster has a control plane and worker nodes. The API server accepts declared objects, the scheduler chooses nodes, controllers reconcile actual state with desired state, and node agents run containers. A Pod is the scheduling unit and may contain cooperating containers sharing its network namespace. A Deployment manages replaceable Pods through ReplicaSets. A Service provides a stable discovery/routing abstraction over selected Pods. A StatefulSet adds stable identity and storage association; it does not automatically implement database replication.

## 2. Declarative reconciliation

You describe the desired state, rather than manually starting every replacement process. Controllers keep observing and attempting to close the difference. Reconciliation is repeated and eventually convergent under suitable conditions; it is not a promise that every request succeeds during change. [Kubernetes controllers](https://kubernetes.io/docs/concepts/architecture/controller/).

```python
# lab: kubernetes_reconcile_model
def reconcile(desired,ready,pending):
    return max(0,desired-ready-pending)
assert reconcile(3,1,1)==1
assert reconcile(3,2,1)==0
assert reconcile(3,3,0)==0
print('Count pending work too; otherwise repeated reconciliation overcreates replacements.')
```

This arithmetic model teaches an invariant, not a Kubernetes API implementation. Real controllers track identities, generations, ownership, health and deletion.

## 3. An annotated deployment recipe

The following generic recipe is a starting configuration for the Python service. Replace the image and supply the named Secret through your deployment process. A separate runnable local K3s capstone exercise appears later in this chapter; its report records the exact workload that was actually tested. Do not assume every example manifest has been applied merely because another cluster test passed.

```yaml recipe
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coach-ai
spec:
  replicas: 2
  selector:
    matchLabels: {app: coach-ai}
  template:
    metadata:
      labels: {app: coach-ai}
    spec:
      automountServiceAccountToken: false
      terminationGracePeriodSeconds: 30
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        seccompProfile: {type: RuntimeDefault}
      containers:
        - name: ai
          image: YOUR_REGISTRY/coach-ai:TESTED_RELEASE
          ports: [{containerPort: 8092}]
          env:
            - name: COACH_SERVICE_TOKEN
              valueFrom:
                secretKeyRef: {name: coach-ai-auth, key: service-token}
          resources:
            requests: {cpu: 250m, memory: 256Mi}
            limits: {cpu: '1', memory: 512Mi}
          securityContext:
            allowPrivilegeEscalation: false
            capabilities: {drop: [ALL]}
          startupProbe:
            httpGet: {path: /health, port: 8092}
            failureThreshold: 30
            periodSeconds: 5
          readinessProbe:
            httpGet: {path: /health, port: 8092}
            periodSeconds: 5
          livenessProbe:
            httpGet: {path: /health, port: 8092}
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata: {name: coach-ai}
spec:
  selector: {app: coach-ai}
  ports: [{port: 8092, targetPort: 8092}]
```

Check the image's actual non-root permissions, listen address and health route before applying. A read-only root filesystem is useful only after writable temporary paths are supplied. Memory limits must be measured for the selected embedding/model mode; these illustrative values are not model capacity recommendations. Never scale a Java service using local H2 and in-memory sessions to two replicas and call the data/session design shared.

## 4. Three probes, three questions

Startup: has this slow-starting process finished initialising? Readiness: should it currently receive traffic? Liveness: is it stuck enough that restarting may help? A failed readiness probe removes a Pod from ready endpoints without inherently restarting it. Liveness failure can cause restart. A configured startup probe defers readiness/liveness probing until startup succeeds. [Probe semantics](https://kubernetes.io/docs/concepts/workloads/pods/probes/).

Do not make liveness fail merely because a shared database is briefly unavailable; restarting every application may worsen the outage. Readiness may incorporate a carefully bounded dependency check when the application cannot serve useful work without it. Separate these routes in a production implementation; the classroom /health route above cannot establish every dependency guarantee.

## 5. Configuration, identity and network boundaries

ConfigMaps hold non-secret configuration. Secrets provide a Kubernetes object for sensitive values, but base64 is encoding, not encryption. Configure encryption at rest, least-privilege RBAC and a rotation strategy. Workload identity can avoid long-lived cloud credentials when supported by the chosen platform.

Namespaces organise resources; they are not an automatic security boundary. NetworkPolicy requires a compatible network implementation and explicit allowed traffic, including DNS and telemetry. Restrict AI access to the application service, database access to authorized services and public ingress to intended routes. TLS termination, certificate renewal, trusted proxy configuration and request-size limits are application-facing concerns too.

## 6. Capacity, disruption and shutdown

Requests influence scheduling; limits constrain resource use. CPU throttling differs from memory termination. Horizontal autoscaling requires meaningful metrics, a working metrics pipeline and downstream capacity. Doubling web Pods can double database connections without doubling database capacity.

A PodDisruptionBudget constrains supported voluntary disruptions; it does not prevent machine failure or make a single replica highly available. Spread replicas across failure domains where appropriate. On termination, stop accepting new work, drain or cancel in-flight operations, close SSE/WebSocket connections with reconnect support and leave durable jobs recoverable. Reconcile the grace period with actual request deadlines.

## 7. Stateful components and migrations

Use shared PostgreSQL for durable application data, an appropriate shared/session-revocation design for identity, and managed Kafka or an explicitly operated broker cluster. PersistentVolumeClaims request storage; snapshots still need restoration testing. StatefulSet identity is useful but insufficient for backup, failover, fencing and schema compatibility.

Run migrations as a controlled release step or Job with locking and failure visibility. Do not have every replica race a destructive migration. Maintain old/new application compatibility during rolling releases. Helm templates package configuration; Kustomize overlays transform it; GitOps controllers reconcile version-controlled desired state. None validates the business behavior of the resulting deployment.

## 8. Deployment acceptance exercise

In an authorized cluster: build and scan a pinned image, validate manifests, deploy a staging namespace, wait for rollout, test login and authorization, submit/retry a job, disconnect/reconnect a stream, terminate a worker, verify recovery, inspect telemetry and restore test data into a separate database. Then rehearse rollback. Record exact image digests, manifests, timestamps and results.

Interview question: a deployment has three Pods but users lose sessions on refresh. Answer: inspect how session state and cookies are handled across replicas; Pod count does not make in-memory state shared. Sticky routing can mask the issue until a Pod dies. A shared session store or suitably designed stateless credentials plus revocation strategy must match the security requirements.

## 9. A real local controller and application exercise

After the Docker acceptance test succeeds, run setup_k3s_lab.py and `python labs/run_linux_lab.py kubernetes --capstone` as described in the device/setup guide. The runner starts an actual K3s control plane and node in the isolated lab VM. First it requests two small worker Pods, deletes one and checks that a different Pod UID appears, then requests one replica. A controller is like a teacher repeatedly counting students against a seating plan: it creates or removes seats until actual state matches requested state.

Next, the test imports the previously built application images into the cluster runtime and creates a temporary namespace. The Secret supplies credentials, Services supply stable network names, and a persistent volume stores the Java service's H2 file. Non-root Pods have resource bounds and do not receive a service-account token. Readiness checks determine when the services can accept the test request. A port-forward exposes only a loopback test endpoint.

The test submits and approves a real job, waits for Java to call Python through the ai Service, and records the answer. It then deletes the web Pod and checks that its replacement can read the same completed job. The persistent volume outlives a Pod; it does not automatically survive losing its underlying disk. The web Deployment uses one replica and Recreate to avoid concurrent H2 writers. Never increase replicas on this file-database profile as a substitute for deploying a shared database.

The namespace and server are cleaned up after testing. Read kubernetes-report.json for actual outcomes, including partial failures. This is one node on one computer, without public ingress or a cloud load balancer. It teaches real scheduling, reconciliation, service networking and volume reuse while keeping their boundaries explicit.

An actual first-run defect illustrates why node readiness is insufficient. Binding the API only to 127.0.0.1 allowed local kubectl calls and simple Pod reconciliation, but the ClusterIP forwarded in-cluster requests to the node interface. CoreDNS stayed unready and the storage provisioner saw connection refused. The runner now binds the authenticated TLS API to the isolated VM interfaces and explicitly waits for both system Deployments. Application port-forwarding stays loopback-only. A production cluster must also restrict API reachability through its network policy/firewall design. The initial partial report and diagnostic review are retained alongside the rerun.
