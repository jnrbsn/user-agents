import json
import os
import random

import requests
from github import Github
from lxml import html


user_agents_file_name = 'user-agents.json'
user_agents_file_path = os.path.join(
    os.path.dirname(__file__), user_agents_file_name)


_saved_user_agents = None


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
        response = requests.get(
            ''.join((base_url, browser)),
            headers={'User-Agent': random.choice(get_saved_user_agents())},
        )

        elems = html.fromstring(response.text).cssselect('td li span.code')

        browser_uas = []
        for elem in elems:
            ua = elem.text_content().strip()
            if not ua.startswith('Mozilla/5.0 '):
                continue
            browser_uas.append(ua)

        for opsys in ('Win64', 'Macintosh', 'Linux x86_64'):
            for ua in browser_uas:
                if opsys in ua:
                    user_agents.append(ua)
                    break

    return user_agents


def json_dump(obj):
    return json.dumps(obj, indent=4)


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
    old_user_agents_json = json_dump(get_saved_user_agents())
    new_user_agents_json = json_dump(get_latest_user_agents())

    if old_user_agents_json != new_user_agents_json:
        update_files_on_github(new_user_agents_json)
