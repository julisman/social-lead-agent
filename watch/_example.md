# Watch: <what you're hunting, in one line>

**Looking for:** one sentence. Be concrete — "urgent-sale (BU) houses and land in
Bali at below-market asking prices", not "property deals".

**Account:** <brand-slug> / <platform> — which logged-in session to browse from.
`bin/guard.sh` is checked for it every run; a parked account skips the watch.

## Queries

Search phrases, broad ones first (Threads token-matching widens with every word):

- `<phrase 1>`
- `<phrase 2>`

Tag feeds, if you've found any (`serp_type=tags` URLs — precise but low-volume):

- `<tag>` — `https://www.threads.com/search?q=<tag>&serp_type=tags&tag_id=<id>`

Record known noise here as you discover it — token collisions, name-alike places,
seller spam — so the next run doesn't rediscover it.

## Counts as a hit

The judgement rules, all of which must hold. Keyword match alone is never a hit.
Typical shape:

1. **Category** — what the thing actually is.
2. **Location** — named in the post; no location → not a hit.
3. **Selling, not hunting** — a want-ad from another buyer is signal, not a hit.
4. **The signal you actually care about** — urgency markers, a price ceiling,
   owner-direct, whatever separates "listing" from "worth telling me about".

## Capture

Extra fields worth extracting into `data/watch.jsonl` beyond the standard set:
asking price as written, size, area, owner-direct vs agent.
