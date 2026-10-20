import datetime
import logging
import numbers

from .exceptions import InvalidActivity, InvalidExperiment
from .method import execute

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_activity(activity: dict):
    if not activity:
        raise InvalidActivity("empty activity is no activity")

    ref = activity.get("ref")
    if ref is not None:
        if not isinstance(ref, str) or ref == "":
            raise InvalidActivity("reference to activity must be non-empty strings")

    activity_type = activity.get("type")
    if not activity_type:
        raise InvalidActivity("an activity must have a type")

    if activity_type not in ("probe", "action"):
        raise InvalidActivity(f"'{activity_type}' is not a supported activity type")

    if not activity.get("name"):
        raise InvalidActivity("an activity must have a name")

    provider = activity.get("provider")
    if not provider:
        raise InvalidActivity("an activity requires a provider")

    provider_type = provider.get("type")
    if not provider_type:
        raise InvalidActivity("a provider must have a type")

    if provider_type not in ("python", "process", "http"):
        raise InvalidActivity(f"unknown provider type '{provider_type}'")

    if not activity.get("name"):
        raise InvalidActivity("activity must have a name (cannot be empty)")

    timeout = activity.get("timeout")
    if timeout is not None:
        if not isinstance(timeout, numbers.Number):
            raise InvalidActivity("activity timeout must be a number")

    if "background" in activity:
        if not isinstance(activity["background"], bool):
            raise InvalidActivity("activity background must be a boolean")

    return True


def validate_experiment(experiment: dict):
    logger.info("Validating the experiment's syntax")

    if not experiment:
        raise InvalidExperiment("an empty experiment is not an experiment")

    if not experiment.get("title"):
        raise InvalidExperiment("experiment requires a title")

    if not experiment.get("description"):
        raise InvalidExperiment("experiment requires a description")

    tags = experiment.get("tags")
    if tags:
        if list(filter(lambda t: t == "" or not isinstance(t, str), tags)):
            raise InvalidExperiment("experiment tags must be a non-empty string")

    method = experiment.get("method")
    if method is None:
        raise InvalidExperiment(
            "an experiment requires a method, "
            "which can be empty for only checking steady state hypothesis "
        )

    for activity in method:
        validate_activity(activity)

    logger.info("Experiment looks valid")

    return True


# Runs probe activities and checks steady state
def run_steady_state_probes(probe_list, experiment_config: dict):
    probe_outputs = run_activities(probe_list, experiment_config)
    steady_state_met = True

    # Check tolerance met in probe output
    for probe_output in probe_outputs:
        if "tolerance_met" in probe_output:
            if probe_output["tolerance_met"] == False:
                steady_state_met = False

    return {"steady_state_met": steady_state_met, "probes": probe_outputs}


# Runs a list of activities and returns outputs
def run_activities(activity_list: list, experiment_config: dict):
    activities = []
    for activity in activity_list:
        tolerance = False
        if "tolerance" in activity:
            if activity["tolerance"]:
                tolerance = True

        activity_output = execute(
            module=activity["provider"]["module"],
            func=activity["provider"]["func"],
            arguments=activity["provider"]["arguments"],
            tolerance=tolerance,
            experiment_config=experiment_config,
        )

        activity_output["activity"] = activity
        activities.append(activity_output)

    return activities


# Stub for method.execute (Should be deleted)
def execute(
    module: str, func: str, arguments: dict[str], tolerance, experiment_config: dict
):
    start_time = datetime.datetime.now()
    end_time = datetime.datetime.now()
    duration = end_time - start_time

    return {
        "output": True,
        "start": start_time.isoformat(),
        "status": "succeeded",
        "end": end_time.isoformat(),
        "duration": duration.total_seconds(),
        "tolerance_met": True,
    }


def run_experiment(experiment: dict):
    try:
        validate_experiment(experiment)
        experiment_start_time = datetime.datetime.now()
        status = "completed"
        deviated = False

        experiment_journal = {
            "chaoslib-version": "NA",
            "platform": "Linux-5.10.201-213.748.amzn2.x86_64-x86_64-with-glibc2.26",
            "node": "169.254.68.133",
            "experiment": experiment,
            "start": experiment_start_time.isoformat(),
        }

        # Check Pre Execution Steady State Hypothesis
        steady_states = {
            "before": run_steady_state_probes(
                experiment["steady-state-hypothesis"]["probes"],
                experiment["configuration"],
            )
        }

        if steady_states["before"]["steady_state_met"]:
            # Execute Method
            experiment_journal["run"] = run_activities(
                experiment["method"], experiment["configuration"]
            )

            # Check Post Execution Steady State Hypothesis
            steady_states["after"] = run_steady_state_probes(
                experiment["steady-state-hypothesis"]["probes"],
                experiment["configuration"],
            )
            steady_states["during"] = []

            if steady_states["after"]["steady_state_met"] == False:
                deviated = True

        else:
            status = "failed"

        try:
            if experiment["rollbacks"]:
                experiment_journal["rollbacks"] = run_activities(
                    experiment["rollbacks"], experiment["configuration"]
                )
        except KeyError:
            logger.info("No Rollbacks found")

    except Exception as e:
        print(f"Experiment Aborted with Exception: {e}")
        status = "aborted"

    experiment_end_time = datetime.datetime.now()

    experiment_journal["status"] = status
    experiment_journal["deviated"] = deviated
    experiment_journal["steady_states"] = steady_states
    experiment_journal["rollbacks"] = []
    experiment_journal["end"] = experiment_end_time.isoformat()
    experiment_journal["duration"] = (
        experiment_end_time - experiment_start_time
    ).total_seconds()

    # print(experiment_journal)

    return experiment_journal
