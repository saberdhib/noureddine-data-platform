# ADR-0002 — No Kubernetes, no Terraform

**Date:** 2024-06-01  
**Status:** Accepted

## Context

Modern data platforms often use Kubernetes for container orchestration and Terraform for infrastructure-as-code. The question is whether to adopt these for the NOUREDDINE PFE.

## Decision

**Not adopted.** Docker Compose is used for all local infrastructure.

## Consequences

- **Scale justification:** At ~€8–9M ARR with a single-developer PFE, Kubernetes adds Helm charts, RBAC, namespaces, and node scheduling complexity that yields no benefit at this scale.
- **Reproducibility:** `docker compose up` achieves the same single-command reproducibility without a local k8s cluster (minikube/kind), which would require 8+ GB RAM and significant setup time.
- **Terraform:** with a single environment (local Docker), Terraform IaC adds no value. If migrating to AWS, Terraform would be the right tool — this can be added in a production readiness phase.
- ✅ Simpler onboarding, faster iteration, less cognitive overhead.
- ⚠️ Not directly portable to production Kubernetes without a Helm chart layer.

**Future note:** a production deployment would add a Helm chart and Terraform module for AWS EKS + RDS + S3, following the same architecture with swapped primitives.
