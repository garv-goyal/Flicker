{# Use the model's custom +schema (silver/gold) verbatim instead of dbt's
   default <target>_<custom> concatenation, so schemas are clean names. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
