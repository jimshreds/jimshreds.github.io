# jimshreds.github.io

Jekyll site (GitHub Pages) for a blog and the WKDU radio show "No Gall . No Glory". Radio posts are hosted as audio on archive.org and published through a podcast RSS feed.

## Radio show posts

- Posts live in `_posts/` and must be named `YYYY-MM-DD-radioshow.md` (exactly one dot before `md`). A misnamed file is silently skipped by the metadata script.
- Front matter needs `categories: radio` plus `audio_url`, `audio_length`, `audio_mime` and `itunes_duration`. `feed.podcast.xml` only includes radio posts that have `audio_url`.
- The archive.org identifier is taken from the post's `archive.org/details/...` link. Usually `YYYY-MM-DD-no-gall-no-glory`.
- `date:` is conventionally the day after the show; the title and file name use the show date.

## Build steps

New show (creates the post, fetches archive.org metadata, validates):

    python3 scripts/new_show.py 2026-11-21 [--id <archive-identifier>]

If archive.org had no audio yet, fill in later:

    python3 scripts/fetch_archive_metadata.py --all --missing-only --backup --head-fallback

Validate radio posts (errors exit 1; `--strict` also fails on date-mismatch warnings):

    python3 scripts/check_posts.py

Build and verify the feed:

    bundle exec jekyll build
    xmllint --noout _site/feed.podcast.xml && echo "feed ok"

Run `check_posts.py` before building or committing. Other `fetch_archive_metadata.py` flags (`--dry-run`, `--id`, `--report`) are documented in the script and `README.md`.

## Notes

- `scripts/backups/` holds `.bak` copies written by `--backup`; keep them out of `_posts/` so Jekyll doesn't publish them.
- `scripts/archive_report.json` and `scripts/temp_report.json` are generated reports.
- `feed.radio.xml` is an older feed with no audio enclosures; `feed.podcast.xml` is the real podcast feed.
- Known data oddities: `2026-02-29-radioshow.md` has a non-existent date, and several 2026 catch-up posts have file-name dates that differ from their title and archive ID (the checker warns on these).
