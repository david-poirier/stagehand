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


class Runner:
    def __init__(self, *, scenario_file, locations, rehearsal, _debug):
        self.scenario_file = scenario_file
        self.locations = locations
        self.rehearsal = rehearsal
        self.debug = _debug

    def run(self):
        debug.set_debug(self.debug)
        scn = scenario.load(self.scenario_file)
        print("*" * 80)
        for loc in self.locations.split(","):
            print(f"executing scenario '{self.scenario_file}' against location '{loc}'")
            try:
                executor = Executor(
                    scenario=scn, location=loc, rehearsal=self.rehearsal
                )
                executor.run()
                print(
                    f"scenario execution completed with {executor.errors} error(s) in {executor.elapsed_seconds} seconds"
                )
            except Exception as e:
                print("execution failed: {e}")
            print("*" * 80)


class Executor:
    def __init__(self, *, scenario, location, rehearsal):
        self.scenario = scenario
        self.location = location
        self.rehearsal = rehearsal

        url = urllib.parse.urlparse(f"ssh://{self.location}")
        hostname = url.hostname
        port = url.port
        if port is None:
            port = 22
        username = url.username
        if hostname is None or username is None:
            raise ValueError(
                f"can't parse location '{self.location}'; make sure it's in the format 'username@hostname[:port]', e.g. 'root@10.20.30.40'"
            )
        self.hostname = hostname
        self.port = port
        self.username = username

        self.restarts = []
        self.errors = 0

    def run(self):
        self.session = self._start_session()
        start = time.perf_counter()

        # 0. rehearsal start
        if self.rehearsal:
            self._execute_rehearsal_start()

        # 1. package installs
        for pkg in self.scenario.packages:
            if pkg.action == "install":
                self._execute_package_install(pkg)

        # 2. package removes
        for pkg in self.scenario.packages:
            if pkg.action == "remove":
                self._execute_package_remove(pkg)

        # 3. file copies
        for f in self.scenario.files:
            if f.action == "copy":
                self._execute_file_copy(f)

        # 4. file deletes
        for f in self.scenario.files:
            if f.action == "delete":
                self._execute_file_delete(f)

        # 5. restarts
        for svc in self.restarts:
            self._execute_service_restart(svc)

        self.elapsed_seconds = round((time.perf_counter() - start), 2)
        self.session.stop()

    def _start_session(self):
        while True:
            try:
                password = ""
                while password == "":
                    password = getpass.getpass(f"password for '{self.location}': ")
                sess = session.Session(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    password=password,
                )
                sess.start()
                return sess
            except session.SessionAuthError:
                print("incorrect password!")

    def _execute_rehearsal_start(self):
        print(f"starting REHEARSAL (nothing will be changed)... ", end="", flush=True)
        cmd = commands.RehearsalStart()
        cmd_resp = self.session.execute_command(cmd)
        self._process_cmd_resp(cmd_resp)

    def _execute_package_install(self, pkg):
        print(f"installing package '{pkg.name}'... ", end="", flush=True)
        cmd = commands.PackageInstall(package=pkg.name)
        cmd_resp = self.session.execute_command(cmd)
        self._process_cmd_resp(cmd_resp, pkg.restarts)

    def _execute_package_remove(self, pkg):
        print(f"removing package '{pkg.name}'...", end="", flush=True)
        cmd = commands.PackageRemove(package=pkg.name)
        cmd_resp = self.session.execute_command(cmd)
        self._process_cmd_resp(cmd_resp, pkg.restarts)

    def _execute_file_delete(self, f):
        print(f"deleting file '{f.path}'... ", end="", flush=True)
        cmd = commands.FileDelete(path=f.path)
        cmd_resp = self.session.execute_command(cmd)
        self._process_cmd_resp(cmd_resp, f.restarts)

    def _execute_file_copy(self, f):
        print(f"copying file '{f.path}'... ", end="", flush=True)
        cmd = commands.FileGetProps(path=f.path)
        cmd_resp = self.session.execute_command(cmd)

        if (
            f.hash == cmd_resp.hash
            and f.user == cmd_resp.user
            and f.group == cmd_resp.group
            and f.mode == cmd_resp.mode
        ):
            # noop
            print("nothing to do")
            return

        # check if same file
        if f.hash != cmd_resp.hash:
            # no, copy to remote
            if not self.rehearsal:
                self.session.put_data(f.content.encode(), f.path)

                # check again
                cmd = commands.FileGetProps(path=f.path)
                cmd_resp = self.session.execute_command(cmd)
                if f.hash != cmd_resp.hash:
                    # failed
                    print("error: couldn't copy file")
                    self.errors += 1
                    return

        # check user + group + mode
        if (
            f.user != cmd_resp.user
            or f.group != cmd_resp.group
            or f.mode != cmd_resp.mode
        ):
            # doesn't match, modify
            if not self.rehearsal:
                cmd = commands.FileSetProps(
                    path=f.path,
                    user=f.user,
                    group=f.group,
                    mode=f.mode,
                )
                cmd_resp = self.session.execute_command(cmd)
                if cmd_resp.result == "error":
                    print(f"error: {cmd_resp.error}")
                    self.errors += 1
                    return

                # check again
                cmd = commands.FileGetProps(path=f.path)
                cmd_resp = self.session.execute_command(cmd)
                if (
                    f.user != cmd_resp.user
                    or f.group != cmd_resp.group
                    or f.mode != cmd_resp.mode
                ):
                    # failed
                    print("error: couldn't modify file props")
                    self.errors += 1
                    return

        print("done")
        return self._add_restarts(f.restarts)

    def _execute_service_restart(self, service):
        print(f"restarting service '{service}'... ", end="", flush=True)
        cmd = commands.ServiceRestart(service=service)
        cmd_resp = self.session.execute_command(cmd)
        self._process_cmd_resp(cmd_resp)

    def _process_cmd_resp(self, cmd_resp, restarts=[]):
        if cmd_resp.result == "ok":
            print("done")
            self._add_restarts(restarts)
        elif cmd_resp.result == "noop":
            print("nothing to do")
        elif cmd_resp.result == "error":
            print(f"error: {cmd_resp.error}")
            self.errors += 1

    def _add_restarts(self, restarts):
        for r in restarts:
            if r not in self.restarts:
                self.restarts.append(r)
