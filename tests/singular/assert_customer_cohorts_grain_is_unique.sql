-- customer_cohorts has no single-column key (its grain is cohort_month x months_since_first),
-- so unlike every other analytics mart it has no unique/not_null test on a column. Guard the
-- grain directly instead.
select cohort_month, months_since_first, count(*) as n
from {{ ref('customer_cohorts') }}
group by 1, 2
having count(*) > 1
