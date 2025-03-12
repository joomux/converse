import os
from logging import Logger
from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError
from slack_bolt import Ack
from utils.database import Database, DatabaseConfig
import json
# from utils import builder

db = Database(DatabaseConfig())

def open_channel_creator(ack: Ack, body, client: WebClient, logger: Logger):
    ack()
    try:
        # Get user ID and any stored values
        user_id = body["user"]["id"]
        logger.debug("\n\n===================BODY=====================")
        logger.debug(body)
        logger.debug("===================BODY=====================\n\n")
        stored_values = {} #user_inputs.get(user_id, {})
        
        # Open modal with form
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "channels_creator_submission",
                "title": {
                    "type": "plain_text",
                    "text": "Channel Creator"
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Generate Channels"
                },
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "customer_name_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "customer_name",
                            "initial_value": stored_values.get("customer_name", ""),
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Enter customer name..."
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Customer Name"
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "use_case_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "use_case",
                            "initial_value": stored_values.get("use_case", ""),
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Describe your use case for channel creation..."
                            },
                            "multiline": True
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Use Case Description"
                        }
                    }
                ]
            }
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
        
    query = "SELECT builder_options FROM user_builder_selections WHERE user_id = %s AND app_installed_team_id = %s"
    result = db.fetch_one(query, (user_id, app_installed_team_id))["builder_options"]

    logger.debug("DB RESULT")
    logger.debug(result)

    if "option-channels" in result and "selected" in result["option-channels"]:
        logger.info("About to pre-select channels")
        selected_channels = result["option-channels"]["selected"]
        for block in selector["blocks"]: 
        # do we have a matching param based on block_id?
            if block.get("block_id") == "channels_selected":
                logger.debug(f"Match on block_id in params. Working with \"{block.get('block_id')}\"")

                block["element"]["initial_conversations"] = selected_channels
               
            else:
                continue

    client.views_open(trigger_id=trigger_id, view=selector)