from logzero import logger
from time import sleep
import random


def load_generate(load: str = None, count: int = 100):
    pass


def load_generate_demo(target, intensity, load_duration=75):
    logger.info("Starting load generation")
    sleep(load_duration)
    return {
        "response_time": {
            "avg": random.randint(10, 100),
            "max": random.randint(200, 1000),
            "min": random.randint(1, 5),
        },
        "error_count": random.randint(10, 100),
    }
