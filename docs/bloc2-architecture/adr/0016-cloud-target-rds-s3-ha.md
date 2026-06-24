# ADR-0016 — Cloud target architecture: RDS Multi-AZ + S3 for durability & availability

**Date:** 2024-06-15  
**Status:** Accepted (target architecture — documented, not implemented in the PFE)

## Context

The local stack (`docker compose`) runs **single-node PostgreSQL** and **single-node MinIO**.
This is excellent for **reproducibility and development**, but it is explicitly **NOT**
resilient, redundant or highly available:

- PostgreSQL = one container, one volume → **single point of failure**. A lost container or
  corrupted volume puts data at risk.
- MinIO single-node has **no erasure coding / replication** (that requires distributed MinIO
  with 4+ drives).

We must document, honestly, what the architecture delivers **today** vs what it is **designed
to deliver in production on AWS**, and avoid over-claiming "high availability" for the local
setup. This matters for the data-availability and architecture-quality assessment.

## Decision

Adopt a **cloud-native, S3-compatible architecture** so the platform is **migration-ready
without rewrite**, and define the **AWS production target** for the data layer:

| Layer | Local (now) | AWS production target |
|-------|-------------|------------------------|
| Object storage (lake) | **MinIO** (S3 API, 1 node) | **Amazon S3** |
| Warehouse / OLTP | **PostgreSQL 16** (1 container) | **Amazon RDS for PostgreSQL, Multi-AZ** |

Because the lake already speaks the **S3 API** (`boto3`/the `minio` SDK) and the warehouse is
**standard PostgreSQL**, migrating is essentially a **change of endpoint + credentials** — no
application rewrite (consistent with ADR-0001).

This ADR records the **target**; provisioning it (Terraform/IaC) is **out of PFE scope** —
disproportionate for a 30-person PME at this stage (consistent with ADR-0002 / ADR-0013 on
avoiding K8s/Terraform now).

## Consequences — what each property comes from (be precise)

| Property | Source in the AWS target | Notes |
|----------|--------------------------|-------|
| **Durability** (no data loss) | **S3**: 99.999999999% (11 nines); **RDS**: automated backups + point-in-time recovery (PITR) | data survives hardware loss |
| **Redundancy** | **S3**: multi-AZ replication built-in; **RDS Multi-AZ**: synchronous standby replica | multiple copies across AZs |
| **Availability (HA)** | **RDS Multi-AZ**: automatic failover to the standby; **S3**: natively HA across AZs | tolerates the loss of one Availability Zone |
| **Resilience / DR** | S3 cross-region replication; RDS snapshots + cross-region copy; defined **RTO/RPO** | recover from a regional disaster |

**Honest scope / caveats:**
- "RDS" alone is **not** HA — the claim requires **Multi-AZ** specifically (single-AZ gives
  backups + PITR but no automatic failover).
- **End-to-end** HA would also require redundifying the application tier (FastAPI, Streamlit,
  Airflow) behind a load balancer across AZs. For a 30-FTE PME, the **data layer is the
  priority**; full app-tier HA is deferred as disproportionate.
- The **local** stack must be presented as **dev/reproducibility**, not as resilient/HA.

**Indicative DR objectives (target):** RPO ≤ 5 min (RDS PITR / continuous backups),
RTO ≤ 1 h (Multi-AZ failover is seconds; restore-from-snapshot is the worst case).

**Migration path:** S3 — switch the endpoint/credentials (see `infra/minio/README.md`);
RDS — restore a `pg_dump`/snapshot of the warehouse and repoint `POSTGRES_HOST`. The DDL,
dbt project and DAGs are unchanged.

## Defensible one-liner

> The data layer is **designed for high availability**: in production, **RDS Multi-AZ**
> (automatic failover + backups + PITR) and **S3** (11-nines durability, multi-AZ replication)
> provide durability, redundancy and availability. Locally, MinIO exposes the **same S3 API**
> and PostgreSQL the same engine, guaranteeing a **1:1 migration without rewrite**. The local
> single-node stack is for reproducibility, **not** a high-availability claim.
