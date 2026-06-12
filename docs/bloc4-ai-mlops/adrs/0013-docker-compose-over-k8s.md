# ADR-0013 — Docker Compose over Kubernetes for the MLOps stack

**Date:** 2026-06-12
**Status:** Accepted

## Context

The Bloc 4 consigne template lists a `/k8s` folder, implying Kubernetes manifests for the ML, API, and monitoring services. We must decide whether to introduce Kubernetes for Bloc 4 or continue with the Docker Compose stack already established in Bloc 2 (ADR-0002, no-K8s) and extended through Bloc 3. This decision must stay consistent with that earlier stance and be defensible at the RNCP oral.

## Decision

**Kubernetes is NOT implemented.** Docker Compose remains the orchestration layer for the entire platform, including the new Bloc 4 services (FastAPI, Streamlit, Evidently jobs, retraining DAGs). The `/k8s` folder from the consigne maps to **NOT IMPLEMENTED**, justified by this ADR.

## Consequences

- ✅ **Right-sized for a 30-FTE PME**: NOUREDDINE is a ~€8–9M ARR brand with batch workloads and low concurrency. The forecasting model trains in seconds and serves a handful of internal users. Kubernetes' value (autoscaling, multi-node scheduling, rolling fleet deploys, self-healing across nodes) addresses problems this scale does not have.
- ✅ **Reproducibility unchanged**: `docker compose up` brings up Postgres, Airflow, FastAPI, Streamlit, Grafana, and the monitoring jobs with one command — the same single-command guarantee K8s would provide, without a local cluster (minikube/kind needs 8+ GB RAM and significant setup).
- ✅ **Consistency**: extends ADR-0002 rather than reopening a locked decision; one orchestration model across all four Blocs.
- ✅ **Lower cognitive + maintenance load**: no Helm charts, RBAC, namespaces, ingress controllers, or operators for a single developer to author and defend.
- ⚠️ **Not directly portable to a managed cluster**: a production move to AWS would add a Helm chart layer and EKS — explicitly out of scope and noted as a production-readiness step.

## Alternatives considered

- **Full Kubernetes (EKS / kind locally)** — disproportionate complexity and resource cost for this scale; rejected, consistent with ADR-0002.
- **Docker Swarm** — lighter than K8s but still adds an orchestration layer with no benefit over Compose at single-host scale; rejected.
- **Hybrid (Compose locally, K8s manifests committed but unused)** — dead, untested config that would be indefensible at defence; rejected in favour of an honest NOT IMPLEMENTED with a migration note.

**Future note:** a production deployment would add a Helm chart and Terraform module for AWS EKS + RDS + S3 + MWAA, reusing the same service boundaries with swapped primitives.
