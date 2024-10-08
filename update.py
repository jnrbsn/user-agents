import json
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone
from itertools import count, product

import requests
from github import Github
from lxml import html


user_agents_file_name = 'user-agents.json'
user_agents_file_path = os.path.join(
    os.path.dirname(__file__), user_agents_file_name)

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

_saved_user_agents = None


class wayback_machine:

    @classmethod
    def timestamped_url(cls, timestamp, url):
        return f'https://web.archive.org/web/{timestamp}/{url}'

    @classmethod
    def save_url(cls, url):
        print(f'Saving URL on web.archive.org: {url}')
        response = requests.post(
            f'https://web.archive.org/save/{url}',
            data={'url': url, 'capture_all': 'on'},
        )
        response.raise_for_status()

    @classmethod
    def get_latest_timestamp(cls, url):
        print(f'Getting latest archived snapshot for URL: {url}')
        try:
            response = requests.get(
                'https://archive.org/wayback/available',
                params={'url': url},
            )
            response.raise_for_status()
            response_data = response.json()
            return response_data['archived_snapshots']['closest']['timestamp']
        except (requests.HTTPError, KeyError):
            response = requests.get(
                'https://web.archive.org/cdx/search/cdx',
                params={
                    'url': url,
                    'output': 'json',
                    'limit': '-1',
                    'fastLatest': 'true',
                    'fl': 'timestamp',
                },
            )
            response.raise_for_status()
            response_data = response.json()
            return response_data[1][0]

    @classmethod
    def get_auto_updated_url(cls, url, max_age_days=7):
        timestamp = cls.get_latest_timestamp(url)

        ts_dt = datetime.strptime(
            timestamp, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
        utc_now = datetime.now(tz=timezone.utc)
        age_days = (utc_now - ts_dt).days

        if age_days >= max_age_days:
            cls.save_url(url)
            for _ in range(6):
                time.sleep(10)
                new_timestamp = cls.get_latest_timestamp(url)
                if new_timestamp > timestamp:
                    print(
                        f'Updated timestamp for URL from {timestamp} to '
                        f'{new_timestamp}: {url}')
                    timestamp = new_timestamp
                    break
            else:
                if age_days >= max_age_days * 2:
                    raise RuntimeError(
                        f'Timestamp for URL is {age_days} days old: {url}')
                else:
                    print(
                        'WARNING: Took longer than 60 seconds to save URL; '
                        'skipping for now')

        return cls.timestamped_url(timestamp, url)


def get_saved_user_agents():
    global _saved_user_agents

    if _saved_user_agents is None:
        with open(user_agents_file_path, 'r') as f:
            _saved_user_agents = json.load(f)

    return _saved_user_agents


def get_latest_user_agents():
    user_agents = []
    base_url = 'https://www.whatismybrowser.com/guides/the-latest-user-agent/'

    for browser in ('chrome', 'firefox', 'safari', 'edge'):
        time.sleep(1)
        url = wayback_machine.get_auto_updated_url(base_url + browser)
        print(f'Getting user agents for {browser}')
        response = requests.get(
            url,
            headers={'User-Agent': random.choice(get_saved_user_agents())},
        )
        if response.status_code >= 400:
            print(response.text)
            response.raise_for_status()

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

    return sorted(set(user_agents))


def json_dump(obj):
    return json.dumps(obj, indent=4).strip() + '\n'


def update_files_on_github(new_user_agents_json):
    print('Updating files on GitHub')
    gh = Github(os.environ['GITHUB_TOKEN'])
    repo = gh.get_repo(os.environ['GITHUB_REPOSITORY'])
    for branch in ('main', 'gh-pages'):
        f = repo.get_contents(user_agents_file_name, ref=branch)
        repo.update_file(
            f.path,
            message=f'Update {user_agents_file_name} on {branch} branch',
            content=new_user_agents_json,
            sha=f.sha,
            branch=branch,
        )


if __name__ == '__main__':
    old_user_agents = get_saved_user_agents()
    old_user_agents_json = json_dump(old_user_agents)
    print(f'old_user_agents = {old_user_agents_json}')
    assert len(old_user_agents) >= 4

    new_user_agents = get_latest_user_agents()
    new_user_agents_json = json_dump(new_user_agents)
    print(f'new_user_agents = {new_user_agents_json}')
    assert len(new_user_agents) >= 4

    if old_user_agents_json != new_user_agents_json:
        update_files_on_github(new_user_agents_json)
