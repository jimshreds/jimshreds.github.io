#!/usr/bin/env python3
"""
Create a radio show post, pull audio metadata from archive.org, and validate.

Usage:
  python3 scripts/new_show.py 2026-11-21
  python3 scripts/new_show.py 2026-11-21 --id 2026-11-21-no-gall-no-glory
"""
import sys
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

TEMPLATE = """---
layout: post
title: "Radio Show: {pretty}"
date: {pubdate}
categories: radio
---


[Listen to No Gall . No Glory now on Archive.org](https://archive.org/details/{ident}).

Sundays 8pm - 10pm EST.<br>
91.7fm in Philadelphia<br>
[wkdu.org everywhere else](https://www.wkdu.org)

Requests<br>
bluesky : [@jimshreds.bsky.social](https://bsky.app/profile/jimshreds.bsky.social)<br>
Threads : [@jimshredss](https://www.threads.net/@jimshredss)<br>
Mastodon : [@jimshreds@mastodon.cloud](https://mastodon.cloud/@jimshreds)<br>
Twitter : [@jimshreds](https://twitter.com/jimshreds)<br>

Play Now

<iframe src="https://archive.org/embed/{ident}" width="500" height="30" frameborder="0" webkitallowfullscreen="true" mozallowfullscreen="true" allowfullscreen></iframe>

1. 
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('date', help='Show date, YYYY-MM-DD')
    ap.add_argument('--id', help='archive.org identifier (default: DATE-no-gall-no-glory)')
    args = ap.parse_args()

    d = datetime.strptime(args.date, '%Y-%m-%d')
    ident = args.id or f'{args.date}-no-gall-no-glory'
    path = Path('_posts') / f'{args.date}-radioshow.md'
    if path.exists():
        sys.exit(f'{path} already exists')

    path.write_text(TEMPLATE.format(
        pretty=f'{d:%B} {d.day} {d.year}',
        pubdate=(d + timedelta(days=1)).strftime('%Y-%m-%d'),
        ident=ident,
    ), encoding='utf-8')
    print('Created', path)

    here = Path(__file__).parent
    fetch = subprocess.run([sys.executable, str(here / 'fetch_archive_metadata.py'),
                            '--backup', '--head-fallback', '--id', ident, str(path)])
    if fetch.returncode != 0:
        print('Metadata fetch failed (audio may not be on archive.org yet). '
              f'Re-run later: python3 scripts/fetch_archive_metadata.py --head-fallback {path}')
    check = subprocess.run([sys.executable, str(here / 'check_posts.py')])
    sys.exit(check.returncode)


if __name__ == '__main__':
    main()
