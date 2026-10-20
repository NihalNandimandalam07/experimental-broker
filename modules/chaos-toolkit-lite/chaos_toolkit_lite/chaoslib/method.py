import importlib
import traceback
import re
from datetime import datetime

__all__ = ["execute"]


# Apply the config values to the arguments list
def apply_config(arguments: dict[str], config: dict):
    pattern = r"\$\{[^}]+\}"

    for arg in arguments:
        if type(arguments[arg]) == str:
            if re.search(pattern, arguments[arg]):
                replace_lst = re.findall(pattern, arguments[arg])
                temp_value = arguments[arg]

                if len(replace_lst) > 1:
                    # If there is a string with mulitple variables
                    for replace_var in replace_lst:
                        temp_value = temp_value.replace(
                            replace_var,
                            str(config[replace_var.replace("${", "").replace("}", "")]),
                        )
                    arguments[arg] = temp_value
                else:
                    arguments[arg] = config[
                        replace_lst[0].replace("${", "").replace("}", "")
                    ]

        # Call function recursively
        if type(arguments[arg]) == dict:
            arguments[arg] = apply_config(arguments[arg], config)

    return arguments


def execute(
    module: str, func: str, arguments: dict, tolerance, experiment_config: dict
):
    apply_config(arguments, experiment_config)

    status_str = {True: "succeeded", False: "failed"}
    success = False
    start_time = datetime.utcnow()

    mod = importlib.import_module(module)
    exec_func = getattr(mod, func)
    exception = []

    try:
        results = exec_func(**arguments)
        success = True
    except Exception as e:
        results = None
        exception = traceback.format_exc().split("\n")

    end_time = datetime.utcnow()
    duration = end_time - start_time
    return_data = {
        "start": start_time.isoformat(),
        "end": end_time.isoformat(),
        "status": status_str[success],
        "duration": duration.total_seconds(),
        "output": results,
    }

    if not success:
        return_data["exception"] = exception

    if tolerance:
        return_data["tolerance_met"] = results == tolerance
    return return_data
