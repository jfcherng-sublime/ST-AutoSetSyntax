from __future__ import annotations

# __future__ must be the first import
from typing import List, TypedDict


class GithubApiTag(TypedDict):
    name: str
    zipball_url: str
    tarball_url: str
    commit: GithubApiTagCommit
    node_id: str


class GithubApiTagCommit(TypedDict):
    sha: str
    url: str


GithubApiTags = List[GithubApiTag]
