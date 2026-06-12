{#
  Write models to the bare custom schema (silver / gold), NOT the dbt default
  "<target_schema>_<custom_schema>" (which produced public_silver / public_gold
  and left the real gold/silver empty). The whole platform — pipeline tests,
  gold views, Grafana and Bloc 4 — reads bare silver/gold.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
