import argparse
import getpass
import hashlib
import io
import inspect
import json
import random
import string
import sys
import time
import urllib.parse

from . import commands
from . import debug
from . import scenario
from . import session


def _start_session(loc):
    url = urllib.parse.urlparse(f"ssh://{loc}")
    hostname = url.hostname
    username = url.username
    port = url.port
    if port is None:
        port = 22
    if hostname is None or username is None:
        print(
            f"can't parse location '{loc}'; make sure it's in the format 'username@hostname[:port]', e.g. 'root@10.20.30.40'"
        )
        return

    while True:
        try:
            password = ""
            while password == "":
                password = getpass.getpass(f"password for '{loc}': ")
            sess = session.Session(
                hostname=hostname, port=port, username=username, password=password
            )
            sess.start()
            return sess
        except session.SessionAuthError:
            print("incorrect password!")

def _execute_scenario(scn, loc):
    sess = _start_session(loc)
    restarts = []
    errors = 0
    start = time.perf_counter()

    # 1. package installs
    for pkg in scn.packages:
        if pkg.action == "install":
            result = _execute_package_install(pkg, sess)
            errors += 1 if result.status == "error" else 0
            _update_restarts(restarts, result)

    # 2. package removes
    for pkg in scn.packages:
        if pkg.action == "remove":
            result = _execute_package_remove(pkg, sess)
            errors += 1 if result.status == "error" else 0
            _update_restarts(restarts, result)

    # 3. file copies
    for f in scn.files:
        if f.action == "copy":
            result = _execute_file_copy(f, sess)
            errors += 1 if result.status == "error" else 0
            _update_restarts(restarts, result)

    # 4. file deletes
    for f in scn.files:
        if f.action == "delete":
            result = _execute_file_delete(f, sess)
            errors += 1 if result.status == "error" else 0
            _update_restarts(restarts, result)

    # 5. restarts
    for svc in restarts:
        result = _execute_service_restart(svc, sess)
        errors += 1 if result.status == "error" else 0

    elapsed_seconds = round((time.perf_counter() - start), 2)
    sess.stop()

    return errors, elapsed_seconds


class ExecutionResult:
    def __init__(
        self,
        *,
        status,
        restarts,
    ):
        self.status = status
        self.restarts = restarts

def _print_cmd_resp(cmd_resp):
    if cmd_resp.result == "ok":
        print("done")
    elif cmd_resp.result == "noop":
        print("nothing to do")
    elif cmd_resp.result == "error":
        print(f"error: {cmd_resp.error}")

def _update_restarts(restarts, result):
    for r in result.restarts:
        if r not in restarts:
            restarts.append(r)


def _result(status, restarts=[]):
    return ExecutionResult(
            status=status,
            restarts=restarts)


def _execute_package_install(pkg, sess):
    print(f"installing package '{pkg.name}'... ", end="", flush=True)
    cmd = commands.PackageInstall(package=pkg.name)
    cmd_resp = sess.execute_command(cmd)
    _print_cmd_resp(cmd_resp)
    if cmd_resp.result == "ok":
        return _result("ok", pkg.restarts)
    return _result(cmd_resp.result)


def _execute_package_remove(pkg, sess):
    print(f"removing package '{pkg.name}'...", end="", flush=True)
    cmd = commands.PackageRemove(package=pkg.name)
    cmd_resp = sess.execute_command(cmd)
    _print_cmd_resp(cmd_resp)
    if cmd_resp.result == "ok":
        return _result("ok", pkg.restarts)
    return _result(cmd_resp.result)


def _execute_file_delete(f, sess):
    print(f"deleting file '{f.path}'... ", end="", flush=True)
    cmd = commands.FileDelete(path=f.path)
    cmd_resp = sess.execute_command(cmd)
    _print_cmd_resp(cmd_resp)
    if cmd_resp.result == "ok":
        return _result("ok", f.restarts)
    return _result(cmd_resp.result)


def _execute_file_copy(f, sess):
    print(f"copying file '{f.path}'... ", end="", flush=True)
    cmd = commands.FileGetProps(path=f.path)
    cmd_resp = sess.execute_command(cmd)

    if (
        f.hash == cmd_resp.hash
        and f.user == cmd_resp.user
        and f.group == cmd_resp.group
        and f.mode == f.mode & cmd_resp.mode
    ):
        # noop
        print("nothing to do")
        return _result("noop")

    # check if same file
    if f.hash != cmd_resp.hash:
        # no, copy to remote
        sess.put_data(f.content.encode(), f.path)

        # check again
        cmd_resp = sess.execute_command(cmd)
        if f.hash != cmd_resp.hash:
            # failed
            print("error: couldn't copy file")
            return _result("error")

    # check user + group + mode
    if (
        f.user != cmd_resp.user
        or f.group != cmd_resp.group
        or f.mode != f.mode & cmd_resp.mode
    ):
        # doesn't match, modify
        cmd = commands.FileSetProps(
            path=f.path,
            user=f.user,
            group=f.group,
            mode=f.mode,
        )

        # check again
        cmd_resp = sess.execute_command(cmd)
        if (
            f.user != cmd_resp.user
            or f.group != cmd_resp.group
            or f.mode != f.mode & cmd_resp.mode
        ):
            # failed
            print("error: couldn't modify file props")
            return _result("error")

    print("done")
    return _result("ok", f.restarts)


def _execute_service_restart(service, sess):
    print(f"restarting service '{service}'... ", end="", flush=True)
    cmd = commands.ServiceRestart(service=service)
    cmd_resp = sess.execute_command(cmd)
    _print_cmd_resp(cmd_resp)
    return _result(cmd_resp.result)


def run(scenario_file, locations, _debug):
    debug.set_debug(_debug)
    scn = scenario.load(scenario_file)
    print("*" * 80)
    for loc in locations.split(","):
        print(f"executing scenario '{scenario_file}' against location '{loc}'")
        errors, elapsed_seconds = _execute_scenario(scn, loc)
        print(f"scenario execution completed with {errors} error(s) in {elapsed_seconds} seconds")
        print("*" * 80)

