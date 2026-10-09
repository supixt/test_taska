# Investigation dataset

All rows are fictional. The rules are in `tasks/data/domain.md`; the supplied seed (`tasks/data/seed.json`,
`seed.sqlite`, `expected-seed-results.json`) is unchanged.

## Files

| File | Content |
| --- | --- |
| `sales.sqlite` | Database the application queries (schema: `tasks/data/schema.sql`) |
| `sales.json` | The same rows as a readable snapshot |
| `reference-cases.json` | Five reference cases with expected results |

Regenerate with `.venv/bin/python -m scripts.build_data`. The output is byte-identical on every run;
`tests/test_build_data.py` checks this and that the committed files are current.

## Generation method

`scripts/build_data.py`, random seed `42`:

- Keeps every seed customer, order, and refund unchanged (C1–C2, O1–O4, RF1–RF3).
- Adds customers C3–C10. Segments cycle `medium`, `small`, `large`, so the third segment always exists.
- Adds 8 July, 9 August and 9 September orders (O5–O30) with random customers, days, and amounts
  (1,000–10,000 cents in steps of 500). Each September order copies an August amount, so gross sales are equal
  in both months and the net-sales change comes from refunds, as in the seed. O22 is dated 2026-09-01 to
  exercise the half-open period boundary.
- Adds five refunds (RF4–RF8) with random amounts of 500 cents up to half the order amount:
  RF4 on a July order; RF5 on 2026-08-31 (last day of August); RF6 in September on an August order
  (cross-month); RF7 and RF8 on September orders.
- Fails the build if the story changes (equal Aug/Sep gross, higher September refunds, lower September net,
  three segments, a cross-month refund, an order with several refunds) or if data validation fails
  (`app/db.py`: ID links, non-negative integer cents, refunds per order not above the order amount,
  `YYYY-MM-DD` dates).

Result: 10 customers, 30 orders, 8 refunds.

## Reference cases

Expected values are computed by the plain-Python calculator in `scripts/build_data.py` (`period_totals`,
`faulty_join_gross`) over the rows, without SQL or application code. The calculator reproduces
`expected-seed-results.json` on the seed rows (tested).

| Case | Check | Expected |
| --- | --- | --- |
| RC1 | Period totals | Aug: gross 60,000, refunds 2,500, net 57,500. Sep: gross 60,000, refunds 10,300, net 49,700. Net change −7,800 |
| RC2 | Multi-refund order counted once | Sep gross 60,000; a raw `orders LEFT JOIN refunds` gives 65,000 (O3 counted twice) |
| RC3 | Segment breakdown sums to totals | Sep large 13,500 / 2,400 / 11,100; medium 13,500 / 2,700 / 10,800; small 33,000 / 5,200 / 27,800 |
| RC4 | Write rejected, failed query counts | `DELETE FROM refunds` rejected, `SELECT FROM orders` errors, database unchanged, 2 attempts used |
| RC5 | Refund discrepancy without a cause | Gross change 0, refunds change +7,800, net change −7,800; refund reasons not established |

All amounts are in cents.

### Manual check

RC1–RC3 and RC5 were re-added by hand from the row listing in `sales.json`:

- Aug orders O1, O2, O13–O21: 5,000 + 5,000 + 9,500 + 8,000 + 1,000 + 7,500 + 3,000 + 6,000 + 7,000 + 6,500
  + 1,500 = 60,000. Sep orders O3, O4, O22–O30 have the same amounts: 60,000.
- Aug refunds by refund date: RF1 1,000 + RF5 1,500 = 2,500. Sep: RF2 2,000 + RF3 1,000 + RF6 2,700 +
  RF7 2,200 + RF8 2,400 = 10,300.
- Sep segments: large O4 + O28 + O30 = 13,500, refund RF8 2,400. Medium O22 + O24 + O26 = 13,500, refund RF6
  2,700 (August order O16, customer C6, refunded in September). Small O3 + O23 + O25 + O27 + O29 = 33,000,
  refunds RF2 + RF3 + RF7 = 5,200. Segments sum to 60,000 / 10,300.
- RC2: O3 is the only September order with more than one refund (two), so the faulty join adds 5,000.

RC4 is a behaviour check of the query tool, not a calculation.

## Assumptions and unresolved ambiguity

- **UTC dates.** Dates are stored as `YYYY-MM-DD` without a time, so they are treated as UTC calendar dates.
- **Segment over time.** `customers.segment` has no history, so a refund uses the customer's current segment.
- **Refund before its order.** The rules do not forbid a refund dated before its order. The generated data never
  does this, but validation does not reject it, to avoid adding a rule.
- **Full refunds and zero-amount orders** are allowed (refunds "at or below" the order amount; the schema allows
  `amount_cents = 0`). The generated data contains neither.
