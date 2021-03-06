#!/usr/bin/env python
# -*- encoding: utf-8

import json
import os
import sys

import requests


def neutral_exit():
    # In the early versions of GitHub Actions, you could use exit code 78 to
    # mark a run as "neutral".
    #
    # This got removed in later versions because it's not ambiguous.
    # https://twitter.com/zeitgeistse/status/1163444737057132547
    #
    # (Can I say "I told you so"?)
    #
    sys.exit(0)


def get_session(github_token):
    sess = requests.Session()
    sess.headers = {
        "Accept": "; ".join([
            "application/vnd.github.v3+json",
            "application/vnd.github.antiope-preview+json",
        ]),
        "Authorization": f"token {github_token}",
        "User-Agent": f"GitHub Actions script in {__file__}"
    }

    def raise_for_status(resp, *args, **kwargs):
        try:
            resp.raise_for_status()
        except Exception:
            print(resp.text)
            sys.exit("Error: Invalid repo, token or network issue!")

    sess.hooks["response"].append(raise_for_status)
    return sess


if __name__ == '__main__':
    github_token = os.environ["INPUT_GITHUB_TOKEN"]
    github_repository = os.environ["GITHUB_REPOSITORY"]

    github_event_path = os.environ["GITHUB_EVENT_PATH"]
    event_data = json.load(open(github_event_path))

    pull_request = event_data["pull_request"]

    sess = get_session(github_token)

    pr_data = sess.get(pull_request["url"]).json()
    pr_user = pr_data["user"]["login"]
    print(f"*** This PR was opened by {pr_user}")

    if pr_user != "estensen":
        print("*** This PR was opened by somebody who isn't me; requires manual merge")
        neutral_exit()

    pr_number = event_data["number"]
    pr_src = pull_request["head"]["ref"]
    pr_dst = pull_request["base"]["ref"]

    print(f"*** Checking pull request #{pr_number}: {pr_src} ~> {pr_dst}")

    pr_title = pr_data["title"]
    print(f"*** Title of PR is {pr_title!r}")
    if pr_title.startswith("[WIP] "):
        print("*** This is a WIP PR, will not merge")
        neutral_exit()

    print("*** This PR is ready to be merged.")
    merge_url = pull_request["url"] + "/merge"
    sess.put(merge_url)

    print("*** Cleaning up PR branch")
    pr_ref = pr_data["head"]["ref"]
    api_base_url = pr_data["base"]["repo"]["url"]
    ref_url = f"{api_base_url}/git/refs/heads/{pr_ref}"
    sess.delete(ref_url)
