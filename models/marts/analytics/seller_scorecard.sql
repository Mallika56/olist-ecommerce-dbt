-- Sellers with enough volume to judge (30+ orders), ranked and tiered.
with sellers as (
    select * from {{ ref('dim_sellers') }} where orders >= 30
)

select
    seller_id,
    state,
    orders,
    revenue,
    late_rate,
    avg_review_score,
    rank() over (order by revenue desc)  as revenue_rank,
    case
        when late_rate >= 0.15 or avg_review_score < 3.8 then 'at risk'
        when late_rate <= 0.05 and avg_review_score >= 4.3 then 'top performer'
        else 'steady'
    end as tier
from sellers
order by revenue desc
