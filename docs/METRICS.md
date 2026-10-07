# Metric definitions

| Metric | Definition |
| --- | --- |
| Units received | Sum of delivered units / sum of ordered units; includes partial receipts |
| On-time rate | Count of fully delivered orders received on/before their due date / count of fully delivered orders |
| Overdue order | Incomplete order with a due date strictly before the fixed snapshot |
| Upcoming order | Incomplete order whose due date is on/after the snapshot |
| Capacity utilization | Total ordered units due in a supplier-month / that supplier's monthly capacity |
| Available capacity | Monthly capacity minus allocated units; negative means overloaded |
| Unit cost | Material + labor + overhead, in synthetic IDR |
| Cost variance | Unit cost / target minus one |
| Weighted unit cost | Sum of order quantity × unit cost / sum of order quantity |
| Milestone complete | Completed date is present |
| Milestone on time | Completed date on/before its planned date |
| Overdue milestone | No completed date and planned date before snapshot |

Completed orders are counted equally in punctuality metrics. There is no grace
period. An order received one day after its due date is late. A partial delivery
does not count as a completed order. Supplier-month calculations represent total
planned order volume, including orders already received, rather than remaining
factory workload. All dates are calendar dates without timezone conversion.

The synthetic generator never records a receipt or completion after the fixed
snapshot. It permits partial receipts and overlapping planned production slots.
Overlapping slots are displayed for review; this is not a scheduling optimizer.
The cost simulator uses the selected category's median synthetic unit cost; it
does not claim to be a market benchmark.
