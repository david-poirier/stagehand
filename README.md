# stagehand

`stagehand` is a rudimentary configuration management tool that deploys `scenarios` to `locations` - it's a metaphor 8:::(

## Overview

`stagehand` is inspired by Ansible (sorry Ansible), in that it doesn't require any agent to be installed on the targets - installing and updating agents is easy in theory but less fun in practice.

`scenarios` are contained in YAML files. They consist of `packages` to install or remove, and `files` to copy or delete. Both `packages` and `files` can trigger service `restarts` at the end of the `scenario` run.

When a Scenario is run the order of execution is:
1. Install `packages`
2. Remove `packages`
3. Copy `files`
4. Delete `files`
5. Restart `services`

## Installation

`stagehand` requires Python 3.6+ on the client and targets. It's been developed and tested on MacOS (client) and Ubuntu 18.04 (agent).

### Client install
```shell
source install.sh
```

This will set up a Python virtual environment, `pip install` some dependencies, `python setup.py develop` the application and you're good to go.

### Location (target) install

Nothing! The client takes care of it, see architecture section below for details.

## Usage

```shell
stagehand --scenario myscenario.yaml --locations root@10.2.3.4,root@10.4.5.6 [--rehearsal] [--debug]
```

... where:

- `--scenario` is a valid Scenario YAML file
- `--locations` is a comma-separated list of `username@hostname[:port]` to SSH into. You'll be prompted for the SSH password(s) as the Scenario gets executed. 
- `--rehearsal` will cause the agent to report on what action **should** be taken - it won't actually do anything.
- `--debug` will cause SSH, SFTP, and client-server communication to be printed to the console (kind of ugly, sorry).

## Scenarios

Scenarios consist of `packages` and `files`.

### Packages

A `package` consists of:
- `name` - the name of the package to install or remove
- `action` - either `install` or `remove`
- `restarts` - (optional) a list of `services` to restart after installing or removing the package

Example:
```yaml
packages:
  - name: apache2
    action: install
  - name: libapache2-mod-php
    action: install
    restarts:
      - apache2
  - name: pastebinit
    action: remove
```

### Files

A `file` consists of:
- `path` - the location to write the file to on the target, e.g. `/var/www/html/index.php`
- `action` - either `copy` or `delete`
- `group` - (required for `copy`) the system group to assign ownership to, e.g. `root`
- `user` - (required for `copy`) the system user to assign ownership to, e.g. `root`
- `mode` - (required for `copy`) the mode to assign to the file, in octal form, e.g. `644`
- `content` - (required for `copy`) the content of the file
- `restarts` - (optional) a list of `services` to restart after copying or deleting the file

Example:
```yaml
files:
  - path: /var/www/html/index.php
    action: copy
    group: root
    user: root
    mode: 644
    content: "<?php\nheader(\"Content-Type: text/plain\");\necho \"Hello, world!\\n\";\n?>"
  - path: /etc/apache2/mods-available/dir.conf
    action: copy
    group: root
    user: root
    mode: 644
    content: "<IfModule mod_dir.c>\nDirectoryIndex index.php\n</IfModule>"
    restarts: 
      - apache2
  - path: /var/www/html/index.html
    action: delete
```

## Design

`stagehand` consists of a Python application on the client side, and a Python script (`agent.py`) on the target side. The client starts an SSH session with the target, copies `agent.py` (and support modules) to the target using SFTP, and invokes it with a shell command. The client then switches to a client-server mode where it sends and receives simple JSON-encoded messages over stdout/stdin. When execution completes the client tells `agent.py` to shutdown, and cleans up the target. No `stagehand` artifacts are left on a target machine once execution completes.

## Features
- Each action in a `scenario` is idempotent - if the machine is already in the desired state no action is taken
- No prereqs or agent installation on targets (assuming standard Ubuntu 18.04 setup)
- Uses [`apt`](https://apt-team.pages.debian.net/python-apt/library/index.html) and [`dbus`](https://dbus.freedesktop.org/doc/dbus-python/index.html) Python modules already present on Ubuntu 18.04 to manage packages and services
- File data, user/group, and mode are treated separately, ensuring files are only copied and modified when necessary
- Supports `rehearsal` mode (dry-run) and `debug` mode (SSH & SFTP commands, protocol messages)
- Doesn't do anything stupid with passwords

## Anti-features
- No [tests](https://github.com/david-poirier/stagehand/blob/main/tests/nope.txt)
- Not much error handling
- Assumes `root`
- Doesn't do anything smart with passwords - you have to enter passwords for each target, every time
- No execution history
- Probably only works on Ubuntu 18.04 targets (and maybe newer Ubuntus and Debians?)
- Uses [kind of bizarre method](https://github.com/david-poirier/stagehand/blob/main/stagehand/session.py#L72) to bootstrap itself into target
- `agent.py` code is weird because it's part of the `scenario` module and it's a script
- Client-server protocol tightly coupled with SSH stdin/out transport, makes debugging on target challenging

## Ideas for improvement
- Make `agent.py` a standalone application with its own vendored dependencies (so no "installation" required), distributed with `stagehand` - this would allow for use of different transport in testing and debugging, getting from scripting, etc
- Make `stagehand` multithreaded so that running on 10,000 targets take the same time as running on 1
- Make `stagehand` useable as a module as well as a CLI
- Store secrets (e.g. SSH passwords) securely so that they don't need to be input each time for each target, which is clearly not scaleable
- Store an execution history somewhere useful, e.g. a database

