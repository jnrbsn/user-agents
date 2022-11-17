#!/bin/python3

import json
import os
import re
import time
from itertools import product

import requests
from lxml import html

web_directory = 'web'
user_agents_file_name = 'user-agents.json'
user_agents_file_path = os.path.join(web_directory, user_agents_file_name)

_os_field_include_patterns = [
    re.compile(r'^windows nt \d+\.\d+$', flags=re.IGNORECASE),
    re.compile(r'^macintosh$', flags=re.IGNORECASE),
    re.compile(r'^linux (x86_64|i686)$', flags=re.IGNORECASE),
]
_os_field_exclude_patterns = [
    re.compile(r'\bwindows mobile\b', flags=re.IGNORECASE),
    re.compile(r'\bxbox\b', flags=re.IGNORECASE),
    re.compile(r'\biphone\b', flags=re.IGNORECASE),
    re.compile(r'\bipad\b', flags=re.IGNORECASE),
    re.compile(r'\bipod\b', flags=re.IGNORECASE),
    re.compile(r'\bandroid\b', flags=re.IGNORECASE),
]


def get_latest_user_agents():
    user_agents = []
    base_url = 'https://www.whatismybrowser.com/guides/the-latest-user-agent/'

    for browser in ('chrome', 'firefox', 'safari', 'edge'):
        time.sleep(1)
        response = requests.get(
            ''.join((base_url, browser)),
        )

        elems = html.fromstring(response.text).cssselect('td li span.code')

        browser_uas = []
        for elem in elems:
            ua = elem.text_content().strip()
            if not ua.startswith('Mozilla/5.0 ('):
                continue
            browser_uas.append(ua)

        for ua in browser_uas:
            os_type = ua[len('Mozilla/5.0 ('):ua.find(')')].lower()
            os_fields = [p.strip() for p in os_type.split(';')]

            if any(p.match(f) for p, f in product(
                    _os_field_exclude_patterns, os_fields)):
                continue

            if any(p.match(f) for p, f in product(
                    _os_field_include_patterns, os_fields)):
                user_agents.append(ua)

    return user_agents


def json_dump(obj):
    return json.dumps(obj, indent=4).strip() + '\n'


if __name__ == '__main__':
    ua = get_latest_user_agents()
    with open(user_agents_file_path, 'w') as f:
        f.writelines(json_dump(ua))
