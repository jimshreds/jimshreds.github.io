#!/usr/bin/env python3
"""
Validate radio show posts before building the podcast feed.
Errors (exit 1): bad file name, missing audio fields, no archive.org link.
Warnings (exit 0, or 1 with --strict): date mismatches between file name, title and archive id.

Checks (for posts within --days of today, default 365):
- file name is YYYY-MM-DD-radioshow.md
- front matter has audio_url, audio_length, audio_mime
- title date (e.g. "Radio Show: October 18 2026") matches the file name date
- archive.org identifier date matches the file name date

Usage:
  python3 scripts/check_posts.py [--days N]
"""
import re
import sys
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

NAME_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})-radioshow\.md$')
REQUIRED = ('audio_url', 'audio_length', 'audio_mime')


def front_matter(text):
    parts = text.split('---', 2)
    fm = {}
    if text.startswith('---') and len(parts) == 3:
        for line in parts[1].splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip().strip('"')
    return fm


def check(path, cutoff):
    problems = []
    warnings = []
    m = NAME_RE.match(path.name)
    if not m:
        return [f'{path.name}: bad file name (expected YYYY-MM-DD-radioshow.md)'], []
    file_date = m.group(1)
    try:
        parsed = datetime.strptime(file_date, '%Y-%m-%d').date()
    except ValueError:
        return [], [f'{path.name}: {file_date} is not a real date']
    if parsed < cutoff:
        return [], []
    text = path.read_text(encoding='utf-8')
    fm = front_matter(text)
    for k in REQUIRED:
        if not fm.get(k):
            problems.append(f'{path.name}: missing {k}')
    title = re.search(r'([A-Z][a-z]+ \d{1,2},? \d{4})', fm.get('title', ''))
    if title:
        try:
            td = datetime.strptime(title.group(1).replace(',', ''), '%B %d %Y').strftime('%Y-%m-%d')
            if td != file_date:
                warnings.append(f'{path.name}: title date {td} != file date {file_date}')
        except ValueError:
            pass
    ident = re.search(r'archive\.org/(?:details|embed)/([\w\-\.]+)', text)
    if not ident:
        problems.append(f'{path.name}: no archive.org link')
    elif not ident.group(1).startswith(file_date):
        warnings.append(f'{path.name}: archive id {ident.group(1)} does not start with {file_date}')
    return problems, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--strict', action='store_true', help='Treat warnings as errors')
    ap.add_argument('--days', type=int, default=365)
    args = ap.parse_args()
    cutoff = date.today() - timedelta(days=args.days)
    problems, warnings = [], []
    for p in sorted(Path('_posts').glob('*radioshow*')):
        e, w = check(p, cutoff)
        problems += e
        warnings += w
    for line in warnings:
        print('WARNING:', line)
    for line in problems:
        print('ERROR:', line)
    if problems or (warnings and args.strict):
        sys.exit(1)
    print('radio posts ok')


if __name__ == '__main__':
    main()
