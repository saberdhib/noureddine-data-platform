# Data Governance Annotation Rules — dbt Models

This document is the hand-written reference for the governance `meta` annotations
carried on every dbt model in `dbt/noureddine/models/`. These annotations tie the
**Bloc 1 governance plan** (classifications, retention, ownership) to the **Bloc 3
dbt transformation layer**, and feed the auto-generated
[`data-asset-catalogue-v2.md`](./data-asset-catalogue-v2.md).

It explains every field, its valid values, and who is responsible for setting it.

---

## Classification scheme (C1 → C4)

Inherited from the Bloc 1 governance plan. Conservative: when in doubt, classify up.

| Code | Name         | Meaning                                            | Examples in this platform |
|------|--------------|----------------------------------------------------|---------------------------|
| C1   | Public       | Can be shared externally without harm.             | (none currently)          |
| C2   | Internal     | Internal-only; commercially sensitive but not PII. | products, inventory, calendar, money columns, surrogate keys |
| C3   | Confidential | Personal data (PII), direct or indirect.           | customers, orders, rag_conversations, customer_id |
| C4   | Restricted   | Highest sensitivity (e.g. raw payment card data).  | **none** — no card data is stored in this platform |

> **Note on C4:** there is deliberately **no C4 column** in this model. Payment
> *status* fields (`paid`/`pending`/`refunded`) are C2 — no PAN, CVV, or card data
> is ever ingested. Do not invent a C4 field.

---

## Model-level `meta` fields

Set once per model, under the model's `meta:` key. Owned primarily by the **model
owner / data steward**, with the data engineer translating it into YAML.

| Field              | Valid values                                  | Who sets it           | Notes |
|--------------------|-----------------------------------------------|-----------------------|-------|
| `classification`   | `C1` `C2` `C3` `C4`                           | Steward / owner       | Highest column classification drives the model. |
| `pii_level`        | `none` `indirect` `direct`                    | Steward               | `direct` = raw identifiers/contact present (e.g. email). `indirect` = customer link via key/FK only. `none` = no personal link. |
| `retention_days`   | integer                                       | Steward (legal input) | 1825 (5y) for customer/PII assets; 3650 (10y) for non-PII reference data; 1095 (3y) for marketing/RAG events. |
| `owner_role`       | string (a role, not a person)                 | Owner                 | Accountable business role. Here: `Head of Operations`. |
| `steward_role`     | string (a role, not a person)                 | Steward               | Operational data steward. Here: `Data Steward — Commerce`. |
| `source_systems`   | list of source tables/systems                 | Data engineer         | Upstream sources, e.g. `["oltp.orders"]` or `["gold.fact_sales", "gold.dim_date"]`. |
| `update_frequency` | `micro_batch_10min` `static`                  | Data engineer         | Staging + facts + reference dims = `micro_batch_10min`; `dim_date` spine = `static`. |
| `quality_tier`     | `bronze` `silver` `gold`                      | Data engineer         | Medallion layer. Staging models = `silver`; marts models = `gold`. |

---

## Column-level `meta` fields

Set per column, under each column's `meta:` key. PII judgement is owned by the
**steward**; `business_definition` and `transformation` are owned by the
**data engineer** (with steward review).

| Field                 | Valid values                                                | Who sets it     | Notes |
|-----------------------|-------------------------------------------------------------|-----------------|-------|
| `pii`                 | `true` `false`                                              | Steward         | Is this column personal data? |
| `pii_category`        | `identifier` `contact` `financial` `behavioral` `none`      | Steward         | `identifier` = customer_id/tracking_number; `contact` = email/name; `financial` = money amounts; `behavioral` = free-text RAG question; `none` = otherwise. |
| `classification`      | `C1` `C2` `C3` `C4`                                         | Steward         | Per-column; can be lower than the model (e.g. surrogate keys are C2 inside a C3 model). |
| `business_definition` | one clear sentence                                          | Data engineer   | Plain-language meaning of the column. Always present. |
| `transformation`      | one sentence / expression                                   | Data engineer   | **Only for derived columns** (e.g. `fact_sales.revenue`, `margin`, `discount`, surrogate `*_key`, aggregate view columns). Omit for pass-through columns. |

### `pii_category` quick rules
- **identifier** — keys that point to a person: `customer_id`, `tracking_number`,
  `customer_key` (FK in the fact).
- **contact** — directly contactable data: `email`, `first_name`, `last_name`.
- **financial** — monetary amounts (commercially sensitive, **not personal**):
  `price_eur`, `cost_eur`, `unit_price`, `line_total`, `total_amount`,
  `discount`, `revenue`, `margin`, `shipping_cost`. These are `pii: false`, `C2`.
- **behavioral** — what a person did/asked: `rag_conversations.question`.
- **none** — everything else (flags, dates, statuses, names of products/events).

---

## Worked judgement calls (precedents)

- **Surrogate keys** (`customer_key`, `product_key`, …) are `pii: false`, `C2` even
  inside a C3 model — they are opaque hashes, not raw identifiers. The *natural*
  `customer_id` remains `pii: true`, `C3`.
- **`dim_customer`** is model-level `C3` / `pii_level: indirect`: it carries
  customer-level rows and the natural `customer_id`, but does **not** expose raw
  email/name, so it is indirect rather than direct.
- **`fact_sales`** is `pii_level: indirect` because it carries `customer_key`
  (FK to a person); its body is otherwise aggregate keys + money.
- **Gold aggregate views** (`v_daily_revenue`, `v_sales_by_calendar_event`,
  `v_top_products`) are `C2` / `pii_level: none` — fully aggregated, no per-person
  rows. This is the DPIA-friendly tier used downstream by Bloc 4 ML/forecasting.
- **Money is C2, never C3/C4.** Commercially sensitive ≠ personal.

---

## Where the annotations surface

1. **dbt docs / catalogue** — `meta` is queryable via the dbt manifest.
2. **Postgres comments** — `+persist_docs` in `dbt_project.yml` writes each model
   and column `description` as a `COMMENT ON` in the warehouse, so governance is
   visible directly in pgAdmin / `\d+`.
3. **Data Asset Catalogue v2** — the markdown report regenerated from these `meta`
   blocks (summary table + per-model column tables).

---

## Regenerating the catalogue

After changing any model `meta`, regenerate the catalogue with the single command
(run from the repo root):

```bash
python scripts/export_governance_catalogue.py
```

This overwrites `docs/bloc1-governance/data-asset-catalogue-v2.md` in place
(idempotent). Commit the regenerated file alongside the YAML change so the
catalogue never drifts from the models.
