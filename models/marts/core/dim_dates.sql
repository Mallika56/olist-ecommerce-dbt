-- Calendar covering every purchase date in the data (Sep 2016 - Oct 2018).
with spine as (
    select cast(range as date) as date_day
    from range(date '2016-09-01', date '2018-11-01', interval 1 day)
)

select
    date_day,
    year(date_day)                          as year,
    month(date_day)                         as month,
    date_trunc('month', date_day)::date     as month_start,
    strftime(date_day, '%Y-%m')             as year_month,
    quarter(date_day)                       as quarter,
    isodow(date_day)                        as iso_day_of_week,   -- 1 = Monday
    strftime(date_day, '%A')                as day_name,
    isodow(date_day) >= 6                   as is_weekend
from spine
