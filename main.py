import glob
import json
import os
import time
from typing import List, Optional, Tuple

import cson
import requests

ENV_ACCESS_TOKEN = 'ACCESS_TOKEN'
ENV_SOURCE_DIR = 'SOURCE_DIR'

DEFAULT_SOURCE_DIR = './source_ex/notes/'

DROPBOX_API_URL = 'https://api.dropboxapi.com/2/paper/docs/create'

STATE_FILE = '.state'
FOLDERS_FILE = 'folders.json'


def list_cson_files() -> List[str]:
    source_dir = os.getenv(ENV_SOURCE_DIR, DEFAULT_SOURCE_DIR)
    pattern = os.path.join(source_dir, "*.cson")

    return sorted(glob.glob(pattern))


def to_note(path: str) -> Tuple[str, str]:
    with open(path, 'r') as f:
        orig_note = cson.load(f)

    folder = orig_note.get('folder', '')

    content = orig_note.get('content')
    if not content:
        return '', folder

    lines = orig_note['content'].split('\n')

    try:
        first_line = lines[0].lstrip()
        if first_line[0] == '#':
            lines = lines[1:]
    except IndexError as e:
        print(e)

    if (tag_line := ' '.join([f'#{tag}' for tag in orig_note['tags']])) != '':
        lines.insert(0, tag_line)

    return orig_note['title'] + '\n' + '\n'.join(lines) + '\n', folder


def post_paper(note: str, access_token: str, folder: Optional[str]):
    arg = {'import_format': 'markdown'}
    if folder:
        arg.update({'parent_folder_id': folder})

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Dropbox-API-Arg': json.dumps(arg),
        'Content-Type': 'application/octet-stream',
    }

    res = requests.post(DROPBOX_API_URL,
                        headers=headers,
                        data=note.encode('utf-8'))
    res.raise_for_status()


def is_skip(path: str) -> bool:
    if not os.path.exists(STATE_FILE):
        return False

    with open(STATE_FILE, 'r') as f:
        return path in [p.strip() for p in f.readlines()]


def save_state(path: str):
    with open(STATE_FILE, 'a') as f:
        f.write(f'{path}\n')


def main():
    access_token = os.environ['ACCESS_TOKEN']

    folder_map = {}
    if os.path.exists(FOLDERS_FILE):
        with open(FOLDERS_FILE, 'r') as f:
            folder_map = json.load(f)

    pathes = list_cson_files()
    note_len = len(pathes)

    for i, p in enumerate(pathes):
        print(f'({i}/{note_len}) File: {p}')
        if is_skip(p):
            print(f'Skip to be in state: {p}')
            continue

        note, folder = to_note(p)

        if note.strip() == '':
            print(f'Skip to be no contents: {p}')
            continue

        folder_key = folder_map.get(folder)
        post_paper(note, access_token, folder_key)

        save_state(p)
        print('Success to save state')

        time.sleep(1)


if __name__ == '__main__':
    main()
