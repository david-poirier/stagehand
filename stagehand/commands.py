########################################################################
# Note: keep classes flat so dict unpacking (fromdict) continues to work
########################################################################


class PackageInstall:
    def __init__(
        self,
        *,
        package,
        name="package-install",
    ):
        self.name = name
        self.package = package


class PackageInstallResponse:
    def __init__(
        self,
        *,
        package,
        result,
        error,
        name="package-install-response",
    ):
        self.name = name
        self.package = package
        self.result = result
        self.error = error


class PackageRemove:
    def __init__(
        self,
        *,
        package,
        name="package-remove",
    ):
        self.name = name
        self.package = package


class PackageRemoveResponse:
    def __init__(
        self,
        *,
        package,
        result,
        error,
        name="package-remove-response",
    ):
        self.name = name
        self.package = package
        self.result = result
        self.error = error


class FileDelete:
    def __init__(
        self,
        *,
        path,
        name="file-delete",
    ):
        self.name = name
        self.path = path


class FileDeleteResponse:
    def __init__(
        self,
        *,
        path,
        result,
        error,
        name="file-delete-response",
    ):
        self.name = name
        self.path = path
        self.result = result
        self.error = error


class FileGetProps:
    def __init__(
        self,
        *,
        path,
        name="file-get-props",
    ):
        self.name = name
        self.path = path


class FileGetPropsResponse:
    def __init__(
        self,
        *,
        path,
        result,
        error,
        hash,
        group,
        user,
        mode,
        name="file-get-props-response",
    ):
        self.name = name
        self.path = path
        self.result = result
        self.error = error
        self.hash = hash
        self.group = group
        self.user = user
        self.mode = mode


class FileSetProps:
    def __init__(
        self,
        *,
        path,
        group,
        user,
        mode,
        name="file-set-props",
    ):
        self.name = name
        self.path = path
        self.group = group
        self.user = user
        self.mode = mode


class FileSetPropsResponse:
    def __init__(
        self,
        *,
        path,
        result,
        error,
        name="file-set-props-response",
    ):
        self.name = name
        self.path = path
        self.result = result
        self.error = error


class ServiceRestart:
    def __init__(
        self,
        *,
        service,
        name="service-restart",
    ):
        self.name = name
        self.service = service


class ServiceRestartResponse:
    def __init__(
        self,
        *,
        service,
        result,
        error,
        name="service-restart-response",
    ):
        self.name = name
        self.service = service
        self.result = result
        self.error = error


def fromdict(d):
    cmd_name = d["name"]
    if cmd_name == "package-install":
        return PackageInstall(**d)
    elif cmd_name == "package-install-response":
        return PackageInstallResponse(**d)
    elif cmd_name == "package-remove":
        return PackageRemove(**d)
    elif cmd_name == "package-remove-response":
        return PackageRemoveResponse(**d)
    elif cmd_name == "file-get-props":
        return FileGetProps(**d)
    elif cmd_name == "file-get-props-response":
        return FileGetPropsResponse(**d)
    elif cmd_name == "file-set-props":
        return FileSetProps(**d)
    elif cmd_name == "file-set-props-response":
        return FileSetPropsResponse(**d)
    elif cmd_name == "file-delete":
        return FileDelete(**d)
    elif cmd_name == "file-delete-response":
        return FileDeleteResponse(**d)
    elif cmd_name == "service-restart":
        return ServiceRestart(**d)
    elif cmd_name == "service-restart-response":
        return ServiceRestartResponse(**d)
