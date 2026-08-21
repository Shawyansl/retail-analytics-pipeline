# Retail Analytics Pipeline — Summary Report

**Source file:** `retail_transactions_denormalized.csv` (1,000,000 rows × 24 columns)
**Transaction period:** 2023-01-01 → 2025-12-31 (1,096 days, no gaps)
**Inventory snapshot period:** 2023-01-01 → 2025-12-31
**Generated from:** the six views in `sql/02_create_analytics_views.sql`, run against the loaded warehouse.

---

## 1. Executive Summary

The pipeline ingested 1,000,000 denormalized transaction rows, resolved them into a star schema of
four dimensions and two fact tables, and retained 997,968 sales (99.80%). The 2,032 rows that did
not make it through were quarantined for a stated reason, not dropped silently.

Over the three-year window the business recorded **1,254,215,424** in gross revenue, gave back
**117,446,353** in discounts (9.36% of gross), and booked **1,136,769,097** in net revenue against
**496,264,712** in gross profit — an overall margin of **43.66%**. Average order value was
**1,139.08** across 3,214,389 units sold.

> Subtracting the first two figures gives 1,136,769,071, which is 26 short of the net revenue above.
> That is not an error: `transform.py` computes each money column from unrounded inputs and then
> rounds all of them to 2 decimals independently, so `net_revenue` is not literally
> `gross_revenue − discount_amount` row by row. The per-row difference never exceeds 0.01 — the
> budget for two independent 2-decimal roundings — and across 997,968 rows it accumulates to 26 on a
> base of 1.14 billion, or 0.0000023%.

Two findings in this data are strong enough to act on:

- **Category margin is where the real variation lives.** Margin ranges from 49.79% (Toys) down to
  36.69% (Automotive) — a 13.11 percentage-point spread that is far outside what random assignment
  produces (see §9). Toys is simultaneously the highest-revenue *and* highest-margin category,
  which is unusual and worth protecting.
- **1,887 product/branch pairs (9.44% of all 20,000) are at or below their reorder level** in the
  most recent snapshot, and all 40 branches are affected. 46 of those pairs are at zero stock.

Three findings that *look* like insights in the charts are, on inspection, **not** actionable:
the branch ranking, the sales-channel ranking, and the top-products-by-revenue ranking are all
explained by mechanics other than performance. §9 shows the tests. Reading them as performance
differences would lead to spending money on nothing.

Revenue is **flat**, not growing: the fitted trend is −1.41 per day against a daily mean of
1,037,198, i.e. −0.00014% per day, and the second half of the period is 0.012% below the first.
Any planning that assumes organic growth in this data has no support.

---

## 2. Sales Trend

| Measure | Value |
|---|---|
| Days covered | 1,096 (2023-01-01 → 2025-12-31) |
| Mean daily net revenue | 1,037,198.08 |
| Standard deviation | 48,450.00 |
| Coefficient of variation | 4.67% |
| Best day | 2023-03-10 — 1,209,859.76 net, 996 orders |
| Worst day | 2024-03-14 — 885,046.64 net, 835 orders |
| Linear trend | −1.41 per day (−0.00014% of the daily mean) |
| First half vs. second half | −0.012% |

Daily revenue is remarkably stable: a 4.67% coefficient of variation over three years means no
seasonality, no weekly cycle, and no trend worth modelling. The best and worst days differ by 37%,
but they are single-day outliers around an otherwise tight distribution — the best day is 3.6
standard deviations above the mean, the worst 3.1 below, which is about what 1,096 draws from a
normal distribution would give you anyway.

**What this means for the business question "how does revenue change over time?":** it does not.
The honest answer for this dataset is that revenue is flat within noise, and that a forecast of
"tomorrow will look like today" cannot be beaten by anything more sophisticated.

---

## 3. Top Products by Revenue

| # | Product | Category | Net revenue | Units | Orders |
|---|---|---|---|---|---|
| 1 | Smart Shirt 246 | Toys | 6,047,811.50 | 6,327 | 1,993 |
| 2 | Eco Desk 36 | Pets | 5,954,842.41 | 6,637 | 2,098 |
| 3 | Mini Ball 403 | Books | 5,948,009.80 | 6,394 | 1,989 |
| 4 | Classic Ball 138 | Travel | 5,839,027.87 | 6,562 | 2,079 |
| 5 | Pro Ball 26 | Toys | 5,761,286.77 | 6,846 | 2,088 |
| 6 | Basic Headphones 207 | Clothing | 5,557,142.29 | 6,752 | 2,044 |
| 7 | Pro Shirt 245 | Sports | 5,472,875.08 | 6,533 | 1,986 |
| 8 | Smart Puzzle 198 | Travel | 5,362,773.44 | 6,564 | 1,995 |
| 9 | Eco Shirt 251 | Garden | 5,319,796.20 | 6,443 | 2,018 |
| 10 | Plus Cream 309 | Grocery | 5,299,055.47 | 6,246 | 1,943 |

The top 10 of 500 products account for **4.98%** of net revenue. That is almost exactly the 2.0%
you would get from a flat distribution multiplied by 2.5 — there is no Pareto concentration here.
The top product out-earns the bottom one (Basic Sneakers 462, 61,986.92) by **97.6×**.

**Important caveat — this ranking is a price ranking, not a demand ranking.** Across all 500
products, revenue correlates with `unit_price` at **0.999** but with units sold at only **0.057**
and with order count at **0.025**. The top-10-by-revenue products average 6,530 units sold versus
6,429 for all 500 products — a 1.6% difference — while their average unit price is **955.07**
versus **390.11**, a 2.4× difference. Only **1 of the 10** top-revenue products also appears in the
top 10 by units sold.

So "Smart Shirt 246 is our best product" means "Smart Shirt 246 is among our most expensive
products." Every product sells at roughly the same rate; revenue rank is set by the price tag. A
merchandising decision that promotes these ten items is promoting expensive items, not popular
ones.

---

## 4. Branch Performance

| Rank | Branch | City | Channel | Net revenue | Orders | AOV |
|---|---|---|---|---|---|---|
| 1 | North Branch 31 | Tehran | store | 28,890,906.72 | 25,167 | 1,147.97 |
| 2 | Express Branch 36 | Tehran | store | 28,794,574.68 | 25,302 | 1,138.04 |
| 3 | Bazaar Branch 23 | Rasht | mobile | 28,770,830.00 | 25,014 | 1,150.19 |
| 4 | North Branch 16 | Rasht | online | 28,757,929.20 | 24,968 | 1,151.79 |
| 5 | Central Branch 1 | Rasht | online | 28,727,316.16 | 24,991 | 1,149.51 |
| … | … | | | | | |
| 38 | Bazaar Branch 19 | Shiraz | mobile | 28,127,604.98 | 25,056 | 1,122.59 |
| 39 | Mall Branch 35 | Isfahan | mobile | 28,072,271.78 | 24,648 | 1,138.93 |
| 40 | Bazaar Branch 25 | Tehran | mobile | 28,013,853.90 | 24,844 | 1,127.59 |

**The gap between the best and worst branch is 3.13%.** Average order value across all 40 branches
spans 1,122.59 to 1,151.79 — a 2.6% band.

**This ranking should not be used.** A permutation test (§9) reshuffled the branch label across all
997,968 sales 200 times, keeping each branch's order count fixed. The reshuffled top/bottom spread
averaged 3.85%, and **90.0% of the random shuffles produced a spread at least as large as the real
one.** In other words, the observed spread is not merely small — it is smaller than what pure chance
typically produces at this sample size.

### Sales channel

| Channel | Net revenue | Orders | AOV | Branches | Net per branch |
|---|---|---|---|---|---|
| online | 369,681,510.13 | 324,318 | 1,139.87 | 13 | 28,437,039 |
| mobile | 311,845,387.88 | 273,982 | 1,138.20 | 11 | 28,349,581 |
| partner | 284,697,738.81 | 250,024 | 1,138.68 | 10 | 28,469,774 |
| store | 170,544,460.35 | 149,644 | 1,139.67 | 6 | 28,424,077 |

Online appears to earn 2.2× what store does. It does not outperform store: it has **13 branches
versus 6**. Normalize by branch count and the four channels sit within **0.42%** of each other; AOV
is within **0.15%**. The channel ranking in the chart is a branch-count ranking.

---

## 5. Category Profitability

| Category | Overall margin | Net revenue | Gross profit |
|---|---|---|---|
| Toys | 49.79% | 81,799,497.79 | 40,730,148.62 |
| Sports | 48.03% | 69,416,875.50 | 33,341,023.26 |
| Grocery | 47.62% | 54,875,383.58 | 26,131,198.67 |
| Pets | 47.58% | 66,593,853.26 | 31,683,610.33 |
| Travel | 46.60% | 52,963,852.08 | 24,682,004.81 |
| Books | 45.70% | 54,435,033.98 | 24,878,394.65 |
| Clothing | 45.45% | 56,879,590.20 | 25,849,944.24 |
| Beauty | 44.67% | 65,550,747.35 | 29,279,316.97 |
| Gaming | 43.11% | 46,355,557.39 | 19,981,664.44 |
| Furniture | 43.07% | 54,277,531.10 | 23,379,997.19 |
| Music | 42.98% | 53,055,983.98 | 22,805,855.12 |
| Garden | 42.50% | 43,206,399.19 | 18,364,570.58 |
| Shoes | 42.00% | 54,103,440.45 | 22,724,840.43 |
| Electronics | 41.64% | 63,380,607.72 | 26,391,069.15 |
| Office | 41.24% | 52,291,863.34 | 21,563,514.17 |
| Home Appliances | 41.12% | 56,764,234.64 | 23,343,249.88 |
| Baby | 41.08% | 52,199,163.06 | 21,443,306.07 |
| Health | 39.03% | 61,566,852.94 | 24,031,462.99 |
| Jewelry | 36.81% | 45,078,555.28 | 16,591,564.77 |
| Automotive | 36.69% | 51,974,074.34 | 19,067,975.71 |

No category is loss-making. The spread from Toys to Automotive is **13.11 percentage points**, and
unlike the branch and channel gaps this one is real: shuffling category labels 200 times produced a
spread averaging only **0.35pp** (95th percentile 0.46pp, maximum 0.58pp). **Not one of the 200
shuffles came close to 13.11pp** — the observed spread is more than twenty times the largest random
result.

The top five by revenue are Toys (81.8M, 49.79% margin), Sports (69.4M, 48.03%), Pets (66.6M,
47.58%), Beauty (65.6M, 44.67%), and Electronics (63.4M, 41.64%). Revenue and margin rank together
at the top — Toys and Sports lead on both — which means the highest-volume categories are not being
bought at the expense of profitability. At the other end, Electronics and Health are high-revenue
but below-average margin: 63.4M and 61.6M of revenue converting at 41.64% and 39.03%.

**This is the one dimension where the data supports a decision.** Moving mix toward the top of this
table raises profit; moving it toward the bottom lowers it. The other rankings in this report cannot
say that.

---

## 6. Customer Lifetime Value

| # | Customer | City | Lifetime net revenue | Orders |
|---|---|---|---|---|
| 1 | Omid Moradi | Tehran | 59,006.68 | 34 |
| 2 | Yasin Karimi | Isfahan | 58,555.56 | 32 |
| 3 | Mina Moradi | Tabriz | 58,530.50 | 38 |
| 4 | Leila Moradi | Karaj | 58,125.14 | 33 |
| 5 | Ali Mohammadi | Qom | 57,535.70 | 33 |

All 50,000 customers made at least one purchase. Mean lifetime value is **22,735.38**, median
**22,101.33** — the two are within 2.9% of each other, so the distribution is symmetric with no
whale tail.

Revenue concentration is correspondingly weak:

| Customer segment | Share of net revenue |
|---|---|
| Top 10% | 16.18% |
| Top 20% | 29.50% |
| Top 50% | 62.61% |

A classic retail book would show the top 20% of customers driving 60–80% of revenue. Here the top
20% drive 29.5% — barely above the 20% that a perfectly flat distribution would give. Customers
average **19.96 orders** each, and the top customer's 34 orders is not far from that mean.

**Implication:** there is no high-value segment to build a loyalty program around, because every
customer is roughly equally valuable. A retention program in this data would have to target
everyone, which usually means targeting no one.

---

## 7. Stockout Risk

Evaluated on the most recent snapshot per product/branch pair (20,000 pairs = 500 products × 40
branches), using the thresholds in `vw_stockout_risk`.

| Status | Definition | Pairs | Share |
|---|---|---|---|
| `at_risk` | stock ≤ reorder level | **1,887** | 9.44% |
| `watch` | stock ≤ reorder level × 1.2 | 373 | 1.87% |
| `ok` | above both | 17,740 | 88.70% |

**All 40 branches have at-risk items.** The most exposed:

| Branch | At-risk pairs |
|---|---|
| Express Branch 34 | 67 |
| West Branch 8 | 60 |
| South Branch 9 | 57 |
| Airport Branch 30 | 56 |
| Bazaar Branch 4 | 54 |

**46 of the 1,887 at-risk pairs are at zero stock.** The deepest deficits are 100 units below the
reorder level — stock 0 against a reorder level of 100. **12 pairs tie at that worst deficit**, so no
single pair is "the worst"; five of the twelve are Pro Ball 26 at Central Branch 7, Smart Puzzle 198
at Outlet Branch 22, Nova Ball 412 at Mall Branch 2, Classic Notebook 253 at North Branch 29, and
Basic Headphones 294 at Bazaar Branch 37.

Five of the 46 zero-stock pairs are on products from the revenue top 10 in §3, covering four distinct
products: **Smart Shirt 246** (the #1 revenue product), **Pro Ball 26**, **Smart Puzzle 198**, and
**Eco Shirt 251**. Those are the ones to replenish first, with the caveat from §3 that high revenue
here means high price rather than high demand.

Unlike the branch and channel rankings, this finding needs no statistical defence — it is a direct
count of positions below a threshold the business itself defined. 1,887 pairs need replenishment and
46 of them are already empty.

---

## 8. Data Quality

Rows are never dropped without a record. Everything removed is written to
`data/processed/rejected_records/` with the reason attached.

| Stage | Rows in | Rows out | Removed |
|---|---|---|---|
| Raw file | — | 1,000,000 | — |
| Exact duplicate removal | 1,000,000 | 999,960 | 40 |
| Transform validation | 999,960 | 997,968 | 1,992 |
| Quality checks | 997,968 | 997,968 | 0 |

**Retention: 99.80%.**

Quarantine reasons (a row may carry more than one):

| Reason | Rows |
|---|---|
| `invalid_quantity` | 1,120 |
| `invalid_stock_quantity` | 450 |
| `duplicate_sale_id` | 256 |
| `discount_out_of_range` | 166 |

**18 quality checks, all passing** on the final tables:

- Primary-key uniqueness on all four dimensions
- Primary-key uniqueness on `fact_sales` (`sale_id`) and on `fact_inventory_snapshot`
  (`snapshot_date, product_id, branch_id`)
- Null checks on all six key sets
- Six foreign-key edges: `dim_products → dim_categories`, `fact_sales → dim_customers /
  dim_products / dim_branches`, and `fact_inventory_snapshot → dim_products / dim_branches`

The checks run in dependency order — any check that can delete a dimension row runs before the
fact→dimension edges are validated — and a final `assert_referential_integrity()` gate
re-verifies all six edges on the finished tables and refuses to start the load if any orphan
remains. Zero rows were rejected at this stage, meaning the transform stage had already produced
a referentially clean set.

Final table sizes:

| Table | Rows |
|---|---|
| `fact_sales` | 997,968 |
| `fact_inventory_snapshot` | 975,478 |
| `dim_customers` | 50,000 |
| `dim_products` | 500 |
| `dim_branches` | 40 |
| `dim_categories` | 20 |

Two known, deliberate behaviours worth stating rather than hiding:

- **Customer email conflicts.** 241 customers appear with more than one email address in the source.
  The pipeline resolves each to the most frequent address, breaking ties by first appearance in the
  file. This also fills 1,003 null emails from other rows belonging to the same customer. A customer
  whose every row has a null email keeps a null email; there are none in this file.
- **Attribute drift.** When a dimension row duplicates because a descriptive attribute changed
  (a product price, a customer's city), the first occurrence is kept and later revisions are
  quarantined. The key itself always stays in the dimension, so no fact row is orphaned by this.

---

## 9. How the Statistical Claims Were Tested

Three of the six required analyses produced rankings that look meaningful in a bar chart but are
artifacts. Rather than report them as findings, each was tested:

| Claim | Test | Result |
|---|---|---|
| Branch ranking is meaningful | Shuffle branch labels across all sales 200×, keeping per-branch order counts; compare top/bottom spread | Observed 3.13%; shuffled mean 3.85%, p95 4.75%. **90.0% of shuffles matched or beat the real spread → noise** |
| Category margin spread is meaningful | Same permutation on category labels | Observed 13.11pp; shuffled mean 0.35pp, max 0.58pp. **0% of shuffles came close → real signal** |
| Top products are best-sellers | Correlate product revenue with price, units, and orders; compare top-10-by-revenue against top-10-by-units | corr(revenue, price) = 0.999; corr(revenue, units) = 0.057; **1/10 overlap → the ranking measures price** |
| Channel ranking reflects performance | Normalize channel revenue by branch count; compare AOV | Net per branch within 0.42%, AOV within 0.15%; branches per channel 13/11/10/6 → **the ranking measures branch count** |

This is the difference between a report and a chart. All five required charts are still produced —
they answer the questions the brief asks — but the branch, channel, and top-product charts should
be read as descriptions of the data, not as evidence about performance.

---

## 10. Recommendations

**Supported by the data:**

1. **Replenish the 1,887 at-risk pairs, starting with the 46 at zero stock.** Prioritise the five
   zero-stock positions that sit on top-10 revenue products — Smart Shirt 246, Pro Ball 26, Smart
   Puzzle 198 and Eco Shirt 251. Every one of the 40 branches has exposure, so this is a systemic
   replenishment problem, not a few bad branches.
2. **Shift product mix toward the high-margin end of §5.** A point of mix moved from Automotive
   (36.69%) to Toys (49.79%) is worth 13 points of margin on the revenue moved. This is the only
   ranking in the report that survives a significance test, and Toys leads on both revenue and
   margin, so the shift does not trade volume for profitability.
3. **Review the 9.36% discount rate.** 117.4M was given away against 496.3M of gross profit —
   discounts are 23.7% the size of total profit. There is no evidence in this data that discounting
   drives volume (daily order counts are flat), so this is the largest single lever visible.

**Explicitly not recommended:**

4. **Do not reallocate investment between branches or channels on the basis of this data.** The
   branch gap is inside the noise band (p = 0.900) and the channel gap is a branch-count artifact.
   If branch performance genuinely matters to the business, it needs a metric that controls for
   catchment size and traffic — revenue per branch cannot answer it here.
5. **Do not build a VIP or loyalty tier.** The top 20% of customers hold 29.5% of revenue and mean
   and median CLV differ by 2.9%. There is no concentrated high-value segment to capture.
6. **Do not treat the top-10 product list as a demand signal.** It is a price ranking; only 1 of the
   10 is also a top-10 seller by units. If the goal is to promote what sells, rank by
   `total_quantity_sold` instead — `vw_product_revenue` already exposes that column.

---

## 11. Limitations

- **The dataset is synthetic and close to uniform.** Transactions appear to be generated by
  sampling products, branches, and customers at near-equal rates. That is why the branch, channel,
  customer, and product-volume distributions are all flat, and why the permutation tests come back
  negative. Real retail data would show seasonality, geographic variation, and Pareto
  concentration. Conclusions about *method* transfer to real data; conclusions about *this
  business* do not.
- **Category margin is the exception and is probably by construction.** The 13.11pp spread is
  statistically unambiguous, but it most likely reflects a per-category cost multiplier in the data
  generator rather than a real merchandising outcome. It is reported as the one real signal because
  it *is* the one real signal in this file — not because it is a discovered market fact.
- **Margin is gross margin only.** `gross_profit = (unit_price − unit_cost) × quantity − discount`.
  There is no shipping, handling, storage, labour, or returns data in the source, so nothing here
  is net profit.
- **Stockout risk uses only the latest snapshot.** The pipeline stores the full 975,478-row
  snapshot history, but §7 evaluates one snapshot per product/branch pair. It reports current
  exposure, not how long a position has been depleted or how fast stock is moving. No sales
  velocity is joined in, so "at risk" means "below the business's own reorder threshold", not
  "will run out in N days".
- **The 2,032 removed rows are not analysed for bias.** They are quarantined with reasons and
  available in `data/processed/rejected_records/`, but this report does not test whether their
  removal skews any segment. At 0.20% of the file the effect on the aggregate figures is small,
  though it need not be uniform across branches or categories.
- **Revenue "flatness" is a property of the generator, not evidence of a mature market.** The
  −0.00014%/day trend and 4.67% coefficient of variation are too clean for real trading data.
  Do not present the flat trend as a business finding.
- **Customer email resolution can pick the wrong address.** Majority vote with a first-appearance
  tie-break is deterministic but not authoritative; there is no source-of-truth field in the
  export to validate against. On this file every conflict is one real address plus one injected
  variant, so the vote lands correctly, but that is a property of this data.
