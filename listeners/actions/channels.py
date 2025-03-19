import os
from logging import Logger
from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError
from slack_bolt import Ack
from utils.database import Database, DatabaseConfig
import json
from utils import builder

db = Database(DatabaseConfig())

def open_channel_creator(ack: Ack, body, client: WebClient, logger: Logger):
    ack()
    logger.info("ACTIONS>OPEN_CHANNEL_CREATOR")

    user_id = body["user"]["id"]
    app_installed_team_id = body["view"]["app_installed_team_id"]
    trigger_id = body["trigger_id"]

    view_path = os.path.join("block_kit", "modal_channels_creator.json")
    with open(view_path, 'r') as file:
        modal = json.load(file)
    try:
        config = builder.get_user_selections(user_id=user_id, app_installed_team_id=app_installed_team_id, logger=logger)
        create_string = config.get("channels", {}).get("create", {}).get("use_case", None)

        for block in modal["blocks"]:
            if logger:
                logger.debug(f"Checking block id {block.get('block_id', None)}")
            if block.get("block_id", None) is "use_case_input" and config.get(block["block_id"], None) is not None:
                if logger:
                    logger.debug(f"Setting value to {block.get('block_id', None)}")
                block["element"]["initial_value"] = create_string

        client.views_open(
            trigger_id=trigger_id,
            view=modal
        )
        
    except Exception as e:
        logger.error(f"Error opening channel creator modal: {e}")


def open_channel_selector(ack: Ack, body, client: WebClient, logger: Logger):
    ack()
    logger.info("CHANNEL SELECTOR MODAL")

    user_id = body["user"]["id"]

    # user_id = body["user"]["id"]
    trigger_id = body["trigger_id"]
    view_path = os.path.join("block_kit", "modal_channel_selector.json")
    with open(view_path, 'r') as file:
        selector = json.load(file)

    # load the current config and set any previously selected channels as default
    app_installed_team_id = body["view"]["app_installed_team_id"]
        
    result = builder.get_user_selections(user_id=user_id, app_installed_team_id=app_installed_team_id, logger=logger)

    logger.debug("DB RESULT")
    logger.debug(result)

    if "channels" not in result: # make sure we have a dict to work with
            result["channels"] = {}
    if "selected" not in result["channels"]:
        result["channels"]["selected"] = []

    if len(result["channels"]["selected"]) > 0:
        logger.info("About to pre-select channels")
        selected_channels = [conv["channel"]["id"] for conv in result["channels"]["selected"] if conv["channel"]["id"] is not None]
        for block in selector["blocks"]: 
        # do we have a matching param based on block_id?
            if block.get("block_id") == "channels_selected":
                logger.debug(f"Match on block_id in params. Working with \"{block.get('block_id')}\"")

                block["element"]["initial_conversations"] = selected_channels
               
            else:
                continue

    client.views_open(trigger_id=trigger_id, view=selector)