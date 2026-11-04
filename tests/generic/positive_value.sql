{#
  Fails for rows where the column is negative (or zero, unless allow_zero=true).
  Usage in YAML:  data_tests: [positive_value]   or   - positive_value: {arguments: {allow_zero: true}}
#}
{% test positive_value(model, column_name, allow_zero=false) %}
select *
from {{ model }}
where {{ column_name }} {{ '<' if allow_zero else '<=' }} 0
{% endtest %}
