import inspect
import io
import json
import random
import string

import paramiko

from . import agent
from . import commands
from . import debug


class Session:
    def __init__(
        self,
        *,
        hostname,
        username,
        password,
        port=22,
    ):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port

        self.session_id = "".join(
            random.choices(string.digits + string.ascii_lowercase, k=10)
        )
        self.remote_dir = f"/tmp/stagehand_{self.session_id}/"

    def start(self):
        try:
            self._connect_ssh()
        except paramiko.ssh_exception.AuthenticationException:
            raise SessionAuthError()
        self._start_agent()

    def stop(self):
        self._stop_agent()
        self._close_ssh()

    def execute_command(self, cmd):
        d = cmd.__dict__
        j = json.dumps(d)
        debug.print(f"==>> {type(cmd).__name__}: {j}")
        self._agent_send(j)

        j = self._agent_recv()
        d = json.loads(j)
        resp_cmd = commands.fromdict(d)
        debug.print(f"<<== {type(resp_cmd).__name__}: {j}")
        return resp_cmd

    def _connect_ssh(self):
        self.ssh = paramiko.client.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        self.ssh.connect(
            self.hostname,
            port=self.port,
            username=self.username,
            password=self.password,
        )

    def _close_ssh(self):
        self.ssh.close()
        self.ssh = None

    def _start_agent(self):
        self._exec_simple_command(f"mkdir -p {self.remote_dir}")
        self._put_file(inspect.getfile(agent), f"{self.remote_dir}agent.py")
        self._put_file(inspect.getfile(commands), f"{self.remote_dir}commands.py")
        stdin, stdout, stderr = self.ssh.exec_command(
            f"cd {self.remote_dir}; python3 agent.py"
        )
        msg = stdout.read(2)
        assert msg == b"OK"
        self._agent = {"stdin": stdin, "stdout": stdout, "stderr": stderr}

    def _stop_agent(self):
        self._agent_send("BYE")
        msg = self._agent["stdout"].read(2)
        assert msg == b"OK"
        self._agent = None
        self._exec_simple_command(f"rm -rf {self.remote_dir}")

    def _agent_send(self, msg):
        msg_len = f"{len(msg):10}"
        msg_bytes = (msg_len + msg).encode("utf-8")
        self._agent["stdin"].write(msg_bytes)
        self._agent["stdin"].flush()

    def _agent_recv(self):
        msg_len = self._agent["stdout"].read(10)
        if msg_len == b"":
            return None
        msg_len = int(msg_len)
        msg_bytes = self._agent["stdout"].read(msg_len)
        msg = msg_bytes.decode("utf-8")
        return msg

    def _exec_simple_command(self, cmd):
        debug.print(f"SSH cmd '{cmd}'")
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        return out, err

    def _put_file(self, local, remote):
        debug.print(f"SFTP putting file '{local}' to '{remote}'")
        sftp = self.ssh.open_sftp()
        sftp.put(local, remote, confirm=True)
        sftp.close()

    def put_data(self, data, remote):
        debug.print(f"SFTP putting data to '{remote}'")
        sftp = self.ssh.open_sftp()
        sftp.putfo(io.BytesIO(data), remote, confirm=True)
        sftp.close()


class SessionAuthError(Exception):
    pass
