import json
import os
import random
import re
import sys
from functools import wraps

import requests
from github import Github


user_agents_file_name = 'user-agents.json'
user_agents_file_path = os.path.join(
    os.path.dirname(__file__), user_agents_file_name)

_saved_user_agents = None


def json_dump(obj):
    return json.dumps(obj, indent=2).strip() + '\n'


def with_cli_status(msg):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            sys.stdout.write(f'{msg}... ')
            sys.stdout.flush()
            try:
                result = func(*args, **kwargs)
            except Exception:
                sys.stdout.write('FAILED\n\n')
                sys.stdout.flush()
                raise
            else:
                sys.stdout.write('OK\n\n')
                sys.stdout.flush()
                return result
        return wrapper
    return decorator


def requests_get(url, params=None):
    params = params or {}
    user_agents = get_saved_user_agents()
    response = requests.get(url, params=params, headers={'User-Agent': random.choice(user_agents)})
    response.raise_for_status()
    return response


def get_saved_user_agents():
    global _saved_user_agents

    if _saved_user_agents is None:
        with open(user_agents_file_path, 'r') as f:
            _saved_user_agents = json.load(f)

    return _saved_user_agents


@with_cli_status('Getting Chrome user agents')
def generate_chrome_user_agents():
    user_agents = []
    platform_channels = (
        ('Mac', ('Stable', 'Extended'), 'Macintosh; Intel Mac OS X 10_15_7'),
        ('Windows', ('Stable', 'Extended'), 'Windows NT 10.0; Win64; x64'),
        ('Linux', ('Stable',), 'X11; Linux x86_64'),
    )
    for platform, channels, ua_platform in platform_channels:
        versions = set()
        for channel in channels:
            response = requests_get(
                'https://chromiumdash.appspot.com/fetch_releases',
                params={
                    'channel': channel,
                    'platform': platform,
                    'num': 10,
                    'offset': 0,
                })
            data = response.json()
            versions.update(int(x['version'].split('.', 1)[0]) for x in data)
        versions = sorted(versions)
        for version in versions[-2:]:
            user_agents.append(
                (f'Mozilla/5.0 ({ua_platform}) AppleWebKit/537.36 (KHTML, like Gecko) '
                    f'Chrome/{version}.0.0.0 Safari/537.36'))
    return user_agents


@with_cli_status('Getting Firefox user agents')
def generate_firefox_user_agents():
    user_agents = []
    ua_platforms = (
        'Macintosh; Intel Mac OS X 10.15',
        'Windows NT 10.0; Win64; x64',
        'X11; Linux x86_64',
        'X11; Ubuntu; Linux x86_64',
    )
    trains = ('esr', 'release')
    versions = set()
    for train in trains:
        response = requests_get(
            'https://whattrainisitnow.com/api/release/schedule/',
            params={'version': train})
        data = response.json()
        versions.add(int(data['version'].split('.', 1)[0]))
    versions = sorted(versions)
    for ua_platform in ua_platforms:
        for version in versions:
            user_agents.append(
                f'Mozilla/5.0 ({ua_platform}; rv:{version}.0) Gecko/20100101 Firefox/{version}.0')
    return user_agents


@with_cli_status('Getting Safari user agents')
def generate_safari_user_agents():
    # XXX: these are not public APIs so I'm trying two different sources
    # to reduce the chance of breakage
    user_agents = []
    sources = (
        (
            'https://developer.apple.com/tutorials/data/index/safari-release-notes',
            lambda data: [
                x['title'] for x in data['interfaceLanguages']['swift'][0]['children']
                if x['type'] == 'article'],
        ),
        (
            'https://developer.apple.com/tutorials/data/documentation/safari-release-notes.json',
            lambda data: [
                x['title'] for x in data['references'].values()
                if x['kind'] == 'article'],
        ),
    )
    exc = None
    for url, title_getter in sources:
        try:
            response = requests_get(url)
            data = response.json()
            versions = set()
            for title in title_getter(data):
                if re.search(r'(?i)\bbeta\b', title):
                    continue
                match = re.search(r'[0-9]+(\.[0-9]+)*', title)
                versions.add(match[0])
            versions = sorted(versions, key=lambda v: tuple(int(x) for x in v.split('.')))
            version = versions[-1]
            break
        except Exception as e:
            exc = e
    else:
        raise RuntimeError('failed to get latest version of Safari') from exc
    user_agents.append(
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) '
        f'Version/{version} Safari/605.1.15')
    return user_agents


@with_cli_status('Getting Edge user agents')
def generate_edge_user_agents():
    user_agents = []
    response = requests_get(
        'https://raw.githubusercontent.com/MicrosoftDocs/Edge-Enterprise/refs/heads/public'
        '/edgeenterprise/microsoft-edge-relnote-stable-channel.md')
    versions = set()
    for line in response.text.splitlines():
        match = re.match(
            r'(?i)^#{2,} +version +([0-9]+)(\.[0-9]+)+ *: *[a-z]+ +[0-9]{1,2} *, *[0-9]{4}', line)
        if match is None:
            continue
        versions.add(int(match[1]))
    versions = sorted(versions)
    version = versions[-1]
    user_agents.append(
        (f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
            f'Chrome/{version}.0.0.0 Safari/537.36 Edg/{version}.0.0.0'))
    return user_agents


def get_latest_user_agents():
    user_agents = []
    user_agents.extend(generate_chrome_user_agents())
    user_agents.extend(generate_firefox_user_agents())
    user_agents.extend(generate_safari_user_agents())
    user_agents.extend(generate_edge_user_agents())
    return user_agents


@with_cli_status('Updating files on GitHub')
def update_files_on_github(new_user_agents_json):
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
    assert len(old_user_agents) >= 7

    new_user_agents = get_latest_user_agents()
    new_user_agents_json = json_dump(new_user_agents)
    print(f'new_user_agents = {new_user_agents_json}')
    assert len(new_user_agents) >= 7

    if old_user_agents_json != new_user_agents_json:
        update_files_on_github(new_user_agents_json)
