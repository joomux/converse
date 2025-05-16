import logging
import random
import json
import os

logging.basicConfig(level=os.environ.get('LOGLEVEL', logging.DEBUG))
logger = logging.getLogger(__name__)

"""
    Takes a string in the format X-Y and returns a min and max value as integers
"""
def parse_range(range: str):
    # ints = range.split('-')
    try:
        ints = [int(i) for i in range.split('-')]
    except ValueError as e:
        logger.error(f"Error converting range to integers: {e}")
        raise
    return {"min": min(ints), "max": max(ints)}


def rand_from_range_string(range: str):
    range_ints = parse_range(range)
    return rand_from_range(
        min=range_ints["min"],
        max=range_ints["max"]
    )

def rand_from_range(min: int, max: int):
    return random.randrange(min, max)


def string_to_list(string: str, separater: str=','):
    return [item.strip() for item in string.split(separater)]


def loading_formatter(posts:str, replies: str, canvas: str, current: str):
    view_path = os.path.join("block_kit", "loading_details.json")
    # with open(view_path, 'r') as file:
    #     content = json.load(file)
    
    with open(view_path, 'r') as file:
        content = file.read()

    content = content.replace("%%posts%%", posts)
    content = content.replace("%%canvas%%", canvas)
    content = content.replace("%%replies%%", replies)
    content = content.replace("%%current%%", current)

    return json.loads(content)


def render_block_kit(template, data):
    json_string = json.dumps(template)
    for key, value in data.items():
        # if isinstance(value, str):
        json_string = json_string.replace("{" + key + "}", str(value))
        # else:
            # return render_block_kit(value, data)
    return json.loads(json_string)