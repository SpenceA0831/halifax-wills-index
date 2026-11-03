# Halifax County wills name index

A searchable index of the will abstracts for Halifax County, North Carolina (Will Books 1 to 4) published at
https://freeafricanamericans.com/halifax.htm. It indexes each will maker, every person given or lent something,
and every enslaved person the wills name, with the will book, page and date for each, and a link back to the source.

- `site/` is what Netlify publishes: `index.html` plus three CSV downloads.
- `src/wills.txt` holds one line per will (citation, date, will maker, recipients, enslaved people named, notes).
- `src/bequests.txt` holds each bequest: who received what, whether it was given or lent, and any condition.
- `src/gen.py` builds the site from those two files: `python3 src/gen.py build-out && cp build-out/index.html build-out/*.csv site/`

The abstracts were parsed automatically from the source page, so check the original entry before relying on a detail.
