import argparse

from . import runner


def stagehand():
    parser = argparse.ArgumentParser(
        description="stagehand - Configuration management done (too) quick"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        help="Scenario file (YAML) which describes the desired state (YAML), e.g. 'myscenario.yaml'",
        required=True,
    )
    parser.add_argument(
        "--locations",
        type=str,
        help="Locations (comma-separated hostnames) to configure, e.g. 'web1.aws.com,web2.aws.com'",
        required=True,
    )
    parser.add_argument(
        "--rehearsal",
        action="store_true",
        help="Report on what action should be taken, without actually doing anything",
        required=False,
        default=False,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Watch messages passed between stagehand and the remote location",
        required=False,
        default=False,
    )

    args = parser.parse_args()
    r = runner.Runner(
        scenario_file=args.scenario,
        locations=args.locations,
        rehearsal=args.rehearsal,
        _debug=args.debug,
    )
    r.run()
