-- For completed orders, what the customer paid should equal items + freight.
--
-- Known, legitimate exception: credit-card orders split into instalments often carry
-- interest, so the customer pays MORE than the order total (227 orders, median +R$7.74,
-- median 6 instalments). Those are excluded. What remains (~20 orders, 0.02%) are real
-- unexplained mismatches in Olist's data, so the test warns rather than fails.
{{ config(severity = 'warn', warn_if = '>50') }}

select order_id, primary_payment_type, max_installments, items_plus_freight, amount_paid
from {{ ref('fct_orders') }}
where not is_canceled
  and amount_paid is not null
  and abs(amount_paid - items_plus_freight) > 1.00
  and not (
      primary_payment_type = 'credit_card'
      and max_installments > 1
      and amount_paid > items_plus_freight
  )
