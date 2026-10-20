import os
import json
import yaml
import requests
from json import JSONDecodeError
from .exceptions import InvalidSource

__all__ = ["load_experiment"]


def load_experiment(experiment_source: str):
    if os.path.exists(experiment_source):
        with open(experiment_source) as f:
            path, extention = os.path.splitext(experiment_source)
            if extention in [".yaml", ".yml"]:
                try:
                    return yaml.safe_load(f)
                except Exception as e:
                    raise InvalidSource(f"Failed parsing YAML experiment {str(e)}")
            elif extention == ".json":
                return json.load(f)
            else:
                raise InvalidSource(
                    f"Unable to load experiment, unsupported file type: {extention}"
                )
    else:
        headers = {"Accept": "application/json, application/x-yaml"}
        r = requests.get(experiment_source, headers=headers)
        if r.status_code != 200:
            raise InvalidSource(f"Failed to fetch the experiment: {r.text}")
        content_type = r.headers.get("Content-Type")
        if "application/json" in content_type:
            return r.json()
        elif "text/yaml" in content_type or "application/x-yaml" in content_type:
            try:
                return yaml.safe_load(r.text)
            except yaml.YAMLError as e:
                raise InvalidSource(f"Failed parsing YAML experiment: {str(e)}")
        elif "text/plain" in content_type:
            try:
                return json.loads(r.text)
            except JSONDecodeError:
                try:
                    return yaml.safe_load(r.text)
                except yaml.YAMLError:
                    pass
