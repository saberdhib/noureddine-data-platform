# Bloc 2 — Data Architecture Documentation

## Contents

| File | Description |
|------|-------------|
| [architecture.md](architecture.md) | Logical and technical architecture write-up |
| [data-model.md](data-model.md) | ERD, star schema, governance classification |
| [adr/](adr/) | Architecture Decision Records (one per key decision) |
| [diagrams/](diagrams/) | Mermaid source diagrams (`.mmd`) |

## Quick links

- ADR-0001: MinIO over AWS S3
- ADR-0002: No Kubernetes / Terraform
- ADR-0003: PostgreSQL as single OLTP + warehouse engine
- ADR-0004: Airflow skeleton executor choice
- ADR-0005: Medallion schemas inside PostgreSQL
- ADR-0016: Cloud target — RDS Multi-AZ + S3 for durability & availability

## Consigne → Repo Structure Mapping

The official Bloc 2 consigne expects `/terraform /docker /scripts`. This repo uses a
single platform-oriented `infra/` tree (each folder named by function, not the consigne
label), consistent with the same corrective pattern used in Bloc 3 and Bloc 4:

| Consigne | Repo path | Justification |
|----------|-----------|---------------|
| `/terraform` | **NOT IMPLEMENTED** | IaC is disproportionate for a single-host, laptop-runnable stack — ADR-0002. A managed-cloud migration (EKS/RDS/S3) would add Terraform; documented, not built. |
| `/docker` | `infra/docker-compose.yml` + per-service `Dockerfile` | The whole stack is one Compose file; service images live with their service (`api/`, `streamlit/`, `simulator/`). |
| `/scripts` | `infra/scripts/` (`up.sh`, `down.sh`, `healthcheck.sh`) | Lifecycle + verification scripts. |
| (DB definition) | `sql/ddl/`, `sql/seed/` + `infra/postgres/init/` | Numbered DDL, auto-applied on first boot. |
| (config) | `.env.example`, `infra/pgadmin/`, `infra/minio/`, `infra/grafana/` | Per-service configuration. |

> Why no Terraform/Kubernetes: ADR-0002 — disproportionate for a ~30-FTE PME running a
> single-host Docker Compose stack. Migration paths to AWS are documented for Q&R.
