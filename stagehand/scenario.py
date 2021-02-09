import hashlib

import yaml


class File:
    def __init__(
        self,
        *,
        path,
        action,
        group=None,
        user=None,
        mode=None,
        content=None,
        restarts=[],
    ):
        self.path = path
        self.action = action
        if action not in ["copy", "delete"]:
            raise ValueError("file.action must be either 'copy' or 'delete'")
        self.group = group
        self.user = user
        self.mode = int(mode, 8) if isinstance(mode, str) else mode
        self.content = content
        self.restarts = restarts
        self.hash = (
            hashlib.blake2b(self.content.encode()).hexdigest() if self.content else None
        )


class Package:
    def __init__(
        self,
        *,
        name,
        action,
        restarts=[],
    ):
        self.name = name
        if action not in ["install", "remove"]:
            raise ValueError("package.action must be either 'add' or 'remove'")
        self.action = action
        self.restarts = restarts


class Scenario:
    def __init__(
        self,
        *,
        files=[],
        packages=[],
    ):
        self.files = _cls_list(files, File)
        self.packages = _cls_list(packages, Package)


def _cls_list(items, cls):
    l = []
    for i in items:
        l.append(cls(**i))
    return l


def load(filename):
    with open(filename, "r") as f:
        d = yaml.safe_load(f)
    s = Scenario(**d)
    return s
