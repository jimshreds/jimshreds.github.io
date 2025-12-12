#!/usr/bin/env python3
"""
Enhanced fetch_archive_metadata.py

Features added:
- --dry-run: don't write files
- --backup: write a .bak copy before editing
- --all: scan `_posts/` for radioshow posts and update them
- --id IDENT: use a provided Archive.org identifier instead of extracting from post
- --head-fallback: if metadata lacks size, perform a HEAD request to get Content-Length

Usage examples:
  python3 fetch_archive_metadata.py _posts/2025-08-30-radioshow.md
  python3 fetch_archive_metadata.py --all
  python3 fetch_archive_metadata.py --id 2025-08-30-nogallnoglory _posts/2025-08-30-radioshow.md

"""

import sys
import re
import json
import argparse
import shutil
from urllib.parse import quote
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from pathlib import Path
import time
from typing import Optional


API_BASE = 'https://archive.org/metadata/'


def find_identifier(text):
    m = re.search(r"archive\.org/(?:details|embed)/([\w\-\.]+)", text)
    return m.group(1) if m else None


def fetch_metadata(identifier: str, timeout: int = 10, retries: int = 2) -> Optional[dict]:
    url = API_BASE + quote(identifier)
    req = Request(url, headers={"User-Agent": "fetch-archive-metadata/1.0"})
    attempt = 0
    while attempt <= retries:
        try:
            with urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except Exception as e:
            # Catch all network-related exceptions (timeout, HTTPError, URLError, etc.)
            attempt += 1
            if attempt > retries:
                print(f'Failed to fetch metadata for {identifier}:', e)
                return None
            sleep = 1.5 ** attempt
            print(f'Retry {attempt}/{retries} for {identifier} after {sleep:.1f}s')
            time.sleep(sleep)


def pick_audio_file(metadata):
    files = metadata.get('files', [])
    preferred = ['mp3', 'ogg', 'm4a']
    for ext in preferred:
        for f in files:
            name = f.get('name','')
            if name.lower().endswith('.' + ext):
                return f
    for f in files:
        fmt = (f.get('format') or '').lower()
        if 'audio' in fmt or fmt.startswith('mp3'):
            return f
    return None


def head_content_length(url: str, timeout: int = 10, retries: int = 2) -> Optional[str]:
    req = Request(url, method='HEAD', headers={"User-Agent": "fetch-archive-metadata/1.0"})
    attempt = 0
    while attempt <= retries:
        try:
            with urlopen(req, timeout=timeout) as resp:
                return resp.getheader('Content-Length')
        except Exception as e:
            attempt += 1
            if attempt > retries:
                print(f'HEAD request failed for {url}:', e)
                return None
            sleep = 1.5 ** attempt
            print(f'HEAD retry {attempt}/{retries} for {url} after {sleep:.1f}s')
            time.sleep(sleep)


def update_post_front_matter(post_path, updates, dry_run=False, backup=False):
    p = Path(post_path)
    content = p.read_text(encoding='utf-8')

    if not content.startswith('---'):
        print('No front-matter found in', post_path)
        return False
    parts = content.split('---', 2)
    if len(parts) < 3:
        print('Unexpected front-matter structure in', post_path)
        return False
    front = parts[1].strip()
    body = parts[2]

    lines = [l for l in front.splitlines()]
    kv = {}
    order = []
    for line in lines:
        if ':' in line:
            key, val = line.split(':',1)
            k = key.strip()
            v = val.strip()
            kv[k] = v
            order.append(k)
        else:
            order.append(line)

    for k,v in updates.items():
        if isinstance(v, str):
            if ':' in v or v.startswith('http') or ' ' in v:
                kv[k] = '"{}"'.format(v.replace('"','\\"'))
            else:
                kv[k] = v
        else:
            kv[k] = str(v)
        if k not in order:
            order.append(k)

    new_front_lines = []
    for k in order:
        if ':' in k and k not in kv:
            # keep raw lines (comments or similar)
            new_front_lines.append(k)
        elif k in kv:
            new_front_lines.append(f"{k}: {kv[k]}")

    new_content = '---\n' + '\n'.join(new_front_lines) + '\n---' + body

    if dry_run:
        print('Dry-run: would update', post_path, 'with', updates)
        return True

    if backup:
        # write backups to scripts/backups/ to avoid Jekyll picking them up from _posts/
        backup_dir = Path('scripts/backups')
        backup_dir.mkdir(parents=True, exist_ok=True)
        bak = backup_dir / (p.name + '.bak')
        shutil.copyfile(p, bak)
        print('Backup written to', bak)

    p.write_text(new_content, encoding='utf-8')
    return True


def process_post(post_path, identifier=None, dry_run=False, backup=False, head_fallback=False, timeout=10, retries=2):
    text = Path(post_path).read_text(encoding='utf-8')
    ident = identifier or find_identifier(text)
    result = {'post': post_path, 'identifier': ident, 'success': False, 'reason': None, 'updates': None}
    if not ident:
        result['reason'] = 'no-identifier'
        print('No Archive.org identifier found for', post_path)
        return result

    print('Using identifier:', ident, 'for', post_path)
    meta = fetch_metadata(ident, timeout=timeout, retries=retries)
    if not meta:
        result['reason'] = 'metadata-fetch-failed'
        return result

    audio_file = pick_audio_file(meta)
    if not audio_file:
        result['reason'] = 'no-audio-file'
        print('No audio file found in Archive.org item for', ident)
        return result

    file_name = audio_file.get('name')
    if not file_name:
        result['reason'] = 'no-file-name'
        print('No file name present for audio file in metadata for', ident)
        return result
    audio_url = f"https://archive.org/download/{ident}/{quote(file_name)}"
    audio_length = audio_file.get('size') or audio_file.get('bytes') or 0
    audio_format = audio_file.get('format') or ''

    if (not audio_length or int(audio_length) == 0) and head_fallback:
        cl = head_content_length(audio_url, timeout=timeout, retries=retries)
        if cl:
            audio_length = cl

    duration = audio_file.get('length') or audio_file.get('duration') or ''
    if duration:
        try:
            dur_sec = int(float(duration))
            h = dur_sec // 3600
            m = (dur_sec % 3600) // 60
            s = dur_sec % 60
            itunes_duration = f"{h:02}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"
        except Exception:
            itunes_duration = str(duration)
    else:
        itunes_duration = ''

    updates = {
        'audio_url': audio_url,
        'audio_length': audio_length,
        'audio_mime': 'audio/mpeg' if 'mp3' in file_name.lower() else audio_format,
    }
    if itunes_duration:
        updates['itunes_duration'] = itunes_duration

    ok = update_post_front_matter(post_path, updates, dry_run=dry_run, backup=backup)
    result['success'] = bool(ok)
    result['updates'] = updates if ok else None
    if not ok:
        result['reason'] = 'update-failed'
    return result


def find_radioshow_posts():
    p = Path('_posts')
    return sorted([str(x) for x in p.glob('*radioshow.md')])


def main():
    parser = argparse.ArgumentParser(description='Fetch Archive.org audio metadata and inject into Jekyll posts')
    parser.add_argument('post', nargs='?', help='Path to the post to update')
    parser.add_argument('--id', help='Archive.org identifier to use')
    parser.add_argument('--all', action='store_true', help='Process all radioshow posts in _posts')
    parser.add_argument('--dry-run', action='store_true', help="Don't write files")
    parser.add_argument('--backup', action='store_true', help='Create .bak backup before editing')
    parser.add_argument('--head-fallback', action='store_true', help='If size missing, HEAD the download URL')
    parser.add_argument('--timeout', type=int, default=10, help='Network timeout in seconds')
    parser.add_argument('--retries', type=int, default=2, help='Number of retries for network calls')
    parser.add_argument('--report', help='Write a JSON report to the given path')

    args = parser.parse_args()

    targets = []
    if args.all:
        targets = find_radioshow_posts()
    elif args.post:
        targets = [args.post]
    else:
        parser.print_help()
        sys.exit(2)

    ok = True
    report = []
    for t in targets:
        res = process_post(t, identifier=args.id, dry_run=args.dry_run, backup=args.backup, head_fallback=args.head_fallback, timeout=args.timeout, retries=args.retries)
        report.append(res)
        if not res.get('success'):
            ok = False

    if args.report:
        try:
            with open(args.report, 'w', encoding='utf-8') as fh:
                json.dump(report, fh, indent=2)
            print('Wrote report to', args.report)
        except Exception as e:
            print('Failed to write report:', e)

    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
