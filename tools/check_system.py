"""Checks run by CI on the system description.

1. system.yaml follows system.schema.json.
2. Every openapi.yaml it points to is a valid OpenAPI document.
3. Every endpoint a service says it calls exists in the called service's openapi.yaml.
4. Every folder and file it names exists.
Exits with 1 and a list of problems if anything is wrong.
"""
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

ROOT = Path(__file__).resolve().parent.parent


def main():
    problems = []
    system = yaml.safe_load((ROOT / "system.yaml").read_text())
    schema = json.loads((ROOT / "system.schema.json").read_text())

    for error in Draft202012Validator(schema).iter_errors(system):
        where = "/".join(str(part) for part in error.path) or "(top level)"
        problems.append(f"system.yaml {where}: {error.message}")
    if problems:          # the rest assumes the shape is right
        return report(problems)

    specs = {}
    for name, service in system["services"].items():
        for key in ("path", "migrations"):
            if not (ROOT / service[key]).is_dir():
                problems.append(f"{name}.{key}: folder {service[key]} does not exist")
        spec_path = ROOT / service["openapi"]
        if not spec_path.is_file():
            problems.append(f"{name}.openapi: file {service['openapi']} does not exist")
            continue
        spec = yaml.safe_load(spec_path.read_text())
        try:
            validate(spec)
        except Exception as error:
            problems.append(f"{service['openapi']} is not valid OpenAPI: {str(error).splitlines()[0]}")
        specs[name] = spec

    for name, service in system["services"].items():
        for call in service.get("calls", []):
            target = call["service"]
            if target not in specs:
                problems.append(f"{name} calls unknown service {target}")
                continue
            for endpoint in call["endpoints"]:
                method, path = endpoint.split(" ", 1)
                operations = specs[target].get("paths", {}).get(path, {})
                if method.lower() not in operations:
                    problems.append(f"{name} calls {endpoint}, which is not in {target}'s openapi.yaml")
            if call["url_env"] not in service["env"]:
                problems.append(f"{name} calls {target} through {call['url_env']}, which is not in its env")

    for target in system["ui"]["calls"]:
        if target not in system["services"]:
            problems.append(f"ui calls unknown service {target}")
    if not (ROOT / system["ui"]["path"]).is_dir():
        problems.append(f"ui.path: folder {system['ui']['path']} does not exist")
    return report(problems)


def report(problems):
    if problems:
        print("system.yaml check failed:")
        for problem in problems:
            print(" -", problem)
        return 1
    print("system.yaml, system.schema.json and both openapi.yaml files are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
