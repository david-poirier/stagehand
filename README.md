# stagehand

`stagehand` is a rudimentary configuration management tool

## Synopsis

`stagehand` deploys `scenarios` to `locations` - it's a metaphor 8:::(

Scenario files are simple YAML. They contain `packages` to install or remove, and `files` to copy or delete. Both `packages` and `files` can trigger service `restarts`.

When a Scenario is run the order of execution is:
1. Install packages
2. Remove packages
3. Copy files
4. Delete files
5. Restart services

## Installation

`stagehand` requires Python 3.6+ on the client and `locations` (targets). It's been developed and tested on MacOS (client) and Ubuntu 18.04 (agent).

### Client install
```shell
source install.sh
```

### Location (target) install

Nothing! The client takes care of it, see architecture section below for details.

## Usage

```shell
stagehand --scenario myscenario.yaml --locations root@10.2.3.4,root@10.4.5.6
```

... where `scenario` is a valid Scenario YAML file and `locations` is a comma-separated list of `username@hostname[:port]` to SSH into. You'll be prompted for the SSH password(s) as the Scenario gets executed.

