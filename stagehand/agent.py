import hashlib
import json
import grp
import os
import os.path
import pwd
import sys
import traceback


_rehearsal = False
_apt_updated = False


def _recv_msg():
    msg_len = int(sys.stdin.read(10))
    if msg_len == 0:
        return

    msg = ""
    while msg_len - len(msg) > 0:
        msg += sys.stdin.read(msg_len)
    return msg


def _send_msg(msg):
    msg_len = f"{len(msg):10}"
    sys.stdout.write(msg_len + msg)
    sys.stdout.flush()


def _install_package(package):
    global _apt_updated

    cache = apt.cache.Cache()
    if not _apt_updated:
        cache.update()
        _apt_updated = True
    cache.open()

    if package not in cache:
        return _result("error", "package not found")
    pkg = cache[package]
    if pkg.is_installed:
        return _result("noop")

    try:

        class LogInstallProgress(apt.progress.base.InstallProgress):
            def fork(self):
                pid = os.fork()
                if pid == 0:
                    logfd = os.open(
                        "dpkg.log", os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644
                    )
                    os.dup2(logfd, 1)
                    os.dup2(logfd, 2)
                return pid

        if not _rehearsal:
            pkg.mark_install()
            cache.commit(install_progress=LogInstallProgress())

        return _result("ok")
    except Exception as e:
        return _result("error", str(e))
    finally:
        cache.close()


def _remove_package(package):
    cache = apt.cache.Cache()
    cache.open()

    if package not in cache:
        return _result("error", "package not found")
    pkg = cache[package]
    if pkg.is_installed == False:
        return _result("noop")

    try:

        class LogInstallProgress(apt.progress.base.InstallProgress):
            def fork(self):
                pid = os.fork()
                if pid == 0:
                    logfd = os.open(
                        "dpkg.log", os.O_RDWR | os.O_APPEND | os.O_CREAT, 0o644
                    )
                    os.dup2(logfd, 1)
                    os.dup2(logfd, 2)
                return pid

        if not _rehearsal:
            pkg.mark_delete()
            cache.commit(install_progress=LogInstallProgress())

        return _result("ok")
    except Exception as e:
        return _result("error", str(e))
    finally:
        cache.close()


def _delete_file(path):
    if not os.path.isfile(path):
        return _result("noop")

    try:
        if not _rehearsal:
            os.remove(path)

        return _result("ok")
    except Exception as e:
        return _result("error", str(e))


def _get_file_props(path):
    if not os.path.isfile(path):
        return _result("ok", data={"hash": "", "user": "", "group": "", "mode": 0})

    with open(path, "rb") as f:
        data = f.read()
    hsh = hashlib.blake2b(data).hexdigest()
    stat = os.stat(path)
    user = pwd.getpwuid(stat.st_uid)[0]
    group = grp.getgrgid(stat.st_gid)[0]
    mode = oct(stat.st_mode)[-3:] # keep perms, throw away the rest
    return _result("ok", data={"hash": hsh, "user": user, "group": group, "mode": mode})


def _set_file_props(path, user, group, mode):
    if not os.path.isfile(path):
        return _result("error", error="file not found")

    try:
        uid = pwd.getpwnam(user)[2]
        gid = grp.getgrnam(group)[2]
        stat = os.stat(path)
        if uid == stat.st_uid and gid == stat.st_gid and _mode_equals(mode, stat.st_mode):
            return _result("noop")

        if not _rehearsal:
            if uid != stat.st_uid or gid != stat.st_gid:
                os.chown(path, uid, gid)
            if not _mode_equals(mode, stat.st_mode):
                os.chmod(path, int(mode, 8))
        return _result("ok")
    except Exception as e:
        return _result("error", error=str(e))

def _restart_service(service):
    try:
        if not _rehearsal:
            bus = dbus.SystemBus()
            systemd = bus.get_object(
                "org.freedesktop.systemd1", "/org/freedesktop/systemd1"
            )
            manager = dbus.Interface(systemd, "org.freedesktop.systemd1.Manager")
            manager.RestartUnit(f"{service}.service", "replace")
        return _result("ok")
    except Exception as e:
        return _result("error", error=str(e))


def _result(result, error="", data={}):
    return {"result": result, "error": error, "data": data}


def _run():
    global _rehearsal

    sys.stdout.write("OK")
    sys.stdout.flush()

    while True:
        msg = _recv_msg()
        if msg is None or msg == "BYE":
            break

        d = json.loads(msg)
        cmd = commands.fromdict(d)

        if cmd.name == "rehearsal-start":
            _rehearsal = True
            cmd_resp = commands.RehearsalStartResponse(result="ok", error="")
        elif cmd.name == "package-install":
            result = _install_package(cmd.package)
            cmd_resp = commands.PackageInstallResponse(
                package=cmd.package,
                result=result["result"],
                error=result["error"],
            )
        elif cmd.name == "package-remove":
            result = _remove_package(cmd.package)
            cmd_resp = commands.PackageRemoveResponse(
                package=cmd.package,
                result=result["result"],
                error=result["error"],
            )
        elif cmd.name == "file-get-props":
            result = _get_file_props(cmd.path)
            cmd_resp = commands.FileGetPropsResponse(
                path=cmd.path,
                result=result["result"],
                error=result["error"],
                hash=result["data"]["hash"],
                user=result["data"]["user"],
                group=result["data"]["group"],
                mode=result["data"]["mode"],
            )
        elif cmd.name == "file-set-props":
            result = _set_file_props(cmd.path, cmd.user, cmd.group, cmd.mode)
            cmd_resp = commands.FileSetPropsResponse(
                path=cmd.path,
                result=result["result"],
                error=result["error"],
            )
        elif cmd.name == "file-delete":
            result = _delete_file(cmd.path)
            cmd_resp = commands.FileDeleteResponse(
                path=cmd.path,
                result=result["result"],
                error=result["error"],
            )
        elif cmd.name == "service-restart":
            result = _restart_service(cmd.service)
            cmd_resp = commands.ServiceRestartResponse(
                service=cmd.service,
                result=result["result"],
                error=result["error"],
            )
        else:
            raise Exception(f"Unknown command: {cmd.name}")

        d = cmd_resp.__dict__
        j = json.dumps(d)
        _send_msg(j)

    sys.stdout.write("OK")
    sys.stdout.flush()


def _log_error(e):
    with open("error.txt", "a") as f:
        f.write(str(e))
        f.write(traceback.format_exc())


def _mode_equals(str_mode, int_mode):
    return str_mode[-3:] == oct(int_mode)[-3:]


if __name__ == "__main__":
    try:
        import apt
        import dbus
        import commands

        _run()
    except Exception as e:
        _log_error(e)
