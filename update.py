import dataclasses
import json
import os
import random
import re
import sys
from dataclasses import dataclass
from functools import wraps
from typing import Literal

import requests
from github import Github


@dataclass
class UserAgentInfo:
    os: Literal["linux", "mac", "windows"]
    os_extra: str
    browser: Literal["chrome", "edge", "firefox", "safari"]
    browser_release_channel: Literal["stable", "esr", "extended"]
    browser_version_major: int
    user_agent: str


user_agents_file_name = "user-agents.json"
user_agents_info_file_name = "user-agents-info.json"
user_agents_file_path = os.path.join(os.path.dirname(__file__), user_agents_file_name)

_saved_user_agents: list[str] | None = None


def json_dump(obj):
    return json.dumps(obj, indent=2).strip() + "\n"


def with_cli_status(msg):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            sys.stdout.write(f"{msg}... ")
            sys.stdout.flush()
            try:
                result = func(*args, **kwargs)
            except Exception:
                sys.stdout.write("FAILED\n\n")
                sys.stdout.flush()
                raise
            else:
                sys.stdout.write("OK\n\n")
                sys.stdout.flush()
                return result

        return wrapper

    return decorator


def requests_get(url, params=None):
    params = params or {}
    user_agents = get_saved_user_agents()
    response = requests.get(
        url, params=params, headers={"User-Agent": random.choice(user_agents)}
    )
    response.raise_for_status()
    return response


def get_saved_user_agents() -> list[str]:
    global _saved_user_agents

    if _saved_user_agents is None:
        with open(user_agents_file_path) as f:
            _saved_user_agents = json.load(f)
            assert _saved_user_agents is not None

    return _saved_user_agents


@with_cli_status("Getting Chrome user agents")
def generate_chrome_user_agents() -> list[UserAgentInfo]:
    user_agents: list[UserAgentInfo] = []
    platform_channels = (
        ("Mac", ("Stable", "Extended"), "Macintosh; Intel Mac OS X 10_15_7"),
        ("Windows", ("Stable", "Extended"), "Windows NT 10.0; Win64; x64"),
        ("Linux", ("Stable",), "X11; Linux x86_64"),
    )
    for platform, channels, ua_platform in platform_channels:
        for channel in channels:
            response = requests_get(
                "https://chromiumdash.appspot.com/fetch_releases",
                params={
                    "channel": channel,
                    "platform": platform,
                    "num": 10,
                    "offset": 0,
                },
            )
            data = response.json()

            versions = set(int(x["version"].split(".", 1)[0]) for x in data)
            versions = sorted(versions)

            for version in versions[-2:]:
                info = UserAgentInfo(
                    os=platform.lower(),
                    os_extra="",
                    browser="chrome",
                    browser_release_channel=channel.lower(),
                    browser_version_major=version,
                    user_agent=(
                        f"Mozilla/5.0 ({ua_platform}) AppleWebKit/537.36 (KHTML, like Gecko) "
                        f"Chrome/{version}.0.0.0 Safari/537.36"
                    ),
                )
                user_agents.append(info)

    return user_agents


@with_cli_status("Getting Firefox user agents")
def generate_firefox_user_agents() -> list[UserAgentInfo]:
    user_agents: list[UserAgentInfo] = []
    ua_platforms = (
        ("mac", "", "Macintosh; Intel Mac OS X 10.15"),
        ("windows", "", "Windows NT 10.0; Win64; x64"),
        ("linux", "", "X11; Linux x86_64"),
        ("linux", "ubuntu-x86-64", "X11; Ubuntu; Linux x86_64"),
    )
    trains = ("esr", "release")
    for os_name, os_extra, ua_platform in ua_platforms:
        for train in trains:
            response = requests_get(
                "https://whattrainisitnow.com/api/release/schedule/",
                params={"version": train},
            )
            data = response.json()
            version = int(data["version"].split(".", 1)[0])
            info = UserAgentInfo(
                os=os_name,
                os_extra=os_extra,
                browser="firefox",
                browser_release_channel=train,
                browser_version_major=version,
                user_agent=f"Mozilla/5.0 ({ua_platform}; rv:{version}.0) Gecko/20100101 Firefox/{version}.0",
            )
            user_agents.append(info)
    return user_agents


@with_cli_status("Getting Safari user agents")
def generate_safari_user_agents() -> list[UserAgentInfo]:
    # XXX: these are not public APIs so I'm trying two different sources
    # to reduce the chance of breakage
    user_agents: list[UserAgentInfo] = []
    sources = (
        (
            "https://developer.apple.com/tutorials/data/index/safari-release-notes",
            lambda data: [
                x["title"]
                for x in data["interfaceLanguages"]["swift"][0]["children"]
                if x["type"] == "article"
            ],
        ),
        (
            "https://developer.apple.com/tutorials/data/documentation/safari-release-notes.json",
            lambda data: [
                x["title"]
                for x in data["references"].values()
                if x["kind"] == "article"
            ],
        ),
    )
    exc = None
    for url, title_getter in sources:
        try:
            response = requests_get(url)
            data = response.json()
            versions = set()
            for title in title_getter(data):
                if re.search(r"(?i)\bbeta\b", title):
                    continue
                match = re.search(r"[0-9]+(\.[0-9]+)*", title)
                versions.add(match[0])
            versions = sorted(
                versions, key=lambda v: tuple(int(x) for x in v.split("."))
            )
            version = versions[-1]
            break
        except Exception as e:
            exc = e
    else:
        raise RuntimeError("failed to get latest version of Safari") from exc
    info = UserAgentInfo(
        os="mac",
        os_extra="",
        browser="safari",
        browser_release_channel="stable",
        browser_version_major=version,
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
            f"Version/{version} Safari/605.1.15"
        ),
    )
    user_agents.append(info)
    return user_agents


@with_cli_status("Getting Edge user agents")
def generate_edge_user_agents() -> UserAgentInfo:
    user_agents: list[UserAgentInfo] = []
    response = requests_get(
        "https://edgeupdates.microsoft.com/api/products?view=enterprise"
    ).json()

    versions = set()
    releases = next(r for r in response if r["Product"] == "Stable")["Releases"]
    for rel in releases:
        platform = rel["Platform"]
        arch = rel["Architecture"]
        if platform != "Windows" or arch != "x64":
            continue

        match = re.search(r"([0-9]+)(?:\.[0-9]+)*", rel["ProductVersion"])
        versions.add(match[1])

    versions = sorted(versions)
    version = versions[-1]
    info = UserAgentInfo(
        os="windows",
        os_extra="",
        browser="edge",
        browser_release_channel="stable",
        browser_version_major=version,
        user_agent=(
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{version}.0.0.0 Safari/537.36 Edg/{version}.0.0.0"
        ),
    )
    user_agents.append(info)
    return user_agents


def get_latest_user_agents_info() -> list[UserAgentInfo]:
    user_agents: list[UserAgentInfo] = []
    user_agents.extend(generate_chrome_user_agents())
    user_agents.extend(generate_firefox_user_agents())
    user_agents.extend(generate_safari_user_agents())
    user_agents.extend(generate_edge_user_agents())
    return user_agents


def get_latest_user_agents_info_list(info: list[UserAgentInfo]) -> list[str]:
    agents = {x.user_agent: 0 for x in info}
    return list(agents.keys())


@with_cli_status("Updating files on GitHub")
def update_files_on_github(
    new_user_agents_json: str, new_user_agents_info_json: str
) -> None:
    gh = Github(os.environ["GITHUB_TOKEN"])
    repo = gh.get_repo(os.environ["GITHUB_REPOSITORY"])
    for branch in ("main", "gh-pages"):
        f = repo.get_contents(user_agents_file_name, ref=branch)
        repo.update_file(
            f.path,
            message=f"Update {user_agents_file_name} on {branch} branch",
            content=new_user_agents_json,
            sha=f.sha,
            branch=branch,
        )

        f = repo.get_contents(user_agents_info_file_name, ref=branch)
        repo.update_file(
            f.path,
            message=f"Update {user_agents_info_file_name} on {branch} branch",
            content=new_user_agents_info_json,
            sha=f.sha,
            branch=branch,
        )


if __name__ == "__main__":
    old_user_agents = get_saved_user_agents()
    old_user_agents_json = json_dump(old_user_agents)
    print(f"old_user_agents = {old_user_agents_json}")
    assert len(old_user_agents) >= 7

    new_user_agents_info = get_latest_user_agents_info()
    new_user_agents_info_json = json_dump(
        [dataclasses.asdict(x) for x in new_user_agents_info]
    )
    new_user_agents = get_latest_user_agents_info_list(new_user_agents_info)
    new_user_agents_json = json_dump(new_user_agents)
    print(f"new_user_agents = {new_user_agents_json}")
    assert len(new_user_agents_info) >= 7

    if old_user_agents_json != new_user_agents_json:
        update_files_on_github(new_user_agents_json, new_user_agents_info_json)
