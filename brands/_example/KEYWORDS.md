# {{DISPLAY_NAME}} — keywords

## Search queries

**Use few broad queries, not many specific ones.** Threads does loose token matching, so
extra words widen the net instead of narrowing it — a three-word query returned rental
ads from two cities 900km away during testing. Start with two or three of the plainest
phrases a customer would type, and let the classifier do the filtering.

```
<plain two-to-three word query>
<the same thing, other common wording>
<English version, if you get foreign visitors>
```

## Negative filters — reject on sight

- Words that mean *selling* rather than *buying* in your market
- Job posts, unrelated products that share a keyword
- Anyone **offering** what you offer: price lists, "DM fast respon", slot counts

## Distinguishing seeker from seller

**This table is the most important part of the file.** In most markets the same keyword
is used by buyers and sellers, and getting it backwards fills your lead list with
competitors — silently, because the counts look healthy.

The general rule: **a buyer asks, a seller announces.** If the post states availability,
a price, a slot count, a deadline, or has a call-to-action, it is a seller.

| Seeker (lead) | Seller (reject) |
|---|---|
| "anyone know where I can get X?" | "X available, DM me" |
| "arriving Tuesday, need X" | "promo this week, from 45k" |
| "recommendations for X that's reliable?" | "ready stock, fast response" |

Watch for the inversion in your own market — write the real phrasings here as you see
them. If a run returns a suspiciously healthy number of high-intent leads, **re-read ten
of them before trusting it**: a run that classified sellers as buyers looks exactly like
a good run from the outside.

## Budget floor

Set `budget_floor` in `config.json`. A stated budget below it is a strong signal in both
directions.

Do not reply to someone whose budget you cannot meet. Answering "sorry, we start at X"
to someone asking for half that is a public advert for being expensive, and it burns
that person under the 30-day dedupe rule across every brand you run.

No stated budget is not a reason to reject — most posts don't mention one.

## Recurring sellers to filter

Keep the handles in a local, gitignored note rather than here, so a shared repo does not
publish a blocklist of named businesses.

## Session log

Record which queries produced leads and which produced nothing, so the list can be
pruned. A query that yields zero across three sessions should be retired. Note new buyer
phrasings you see — recognising them matters more than searching for them.

- _(first run)_
