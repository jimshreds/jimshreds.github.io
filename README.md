# dry run single file
python3 scripts/fetch_archive_metadata.py --dry-run --id 2025-08-30-nogallnoglory _posts/2025-08-30-radioshow.md

# run with backup
python3 scripts/fetch_archive_metadata.py --backup --head-fallback --id 2025-08-30-nogallnoglory _posts/2025-08-30-radioshow.md

# dry run for the whole batch
python3 scripts/fetch_archive_metadata.py --all --dry-run

# then real run with backups and head fallback and a report
python3 scripts/fetch_archive_metadata.py --all --backup --head-fallback --report scripts/archive_report.json

# build whole site
bundle exec jekyll build

# validate
xmllint --noout _site/feed.podcast.xml && echo "feed ok"
