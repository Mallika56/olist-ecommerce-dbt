-- The headline question: how much does a late delivery cost in customer satisfaction?
select
    delivery_bucket,
    count(*)                                                        as orders,
    round(100.0 * count(*) / sum(count(*)) over (), 1)              as pct_of_orders,
    round(avg(review_score), 2)                                     as avg_review_score,
    round(100.0 * avg(case when review_score = 1 then 1 else 0 end), 1) as pct_one_star,
    round(100.0 * avg(case when review_score = 5 then 1 else 0 end), 1) as pct_five_star
from {{ ref('fct_orders') }}
where is_delivered and has_review
group by delivery_bucket
order by delivery_bucket
