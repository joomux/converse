import os
from logging import Logger
from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError
from slack_bolt import Ack
# from utils.database import Database, DatabaseConfig
import json

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
                "callback_id": "channel_creator_submission",
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
    logger.info("BUILDER STEP ONE")

    # user_id = body["user"]["id"]
    trigger_id = body["trigger_id"]
    view_path = os.path.join("block_kit", "modal_channel_selector.json")
    with open(view_path, 'r') as file:
        selector = json.load(file)
    client.views_open(trigger_id=trigger_id, view=selector)