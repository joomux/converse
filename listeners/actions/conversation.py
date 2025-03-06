import os
from logging import Logger
from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError
from slack_bolt import Ack
import json
# from utils.database import Database, DatabaseConfig

def channel_designer(ack: Ack, client: WebClient, body, logger: Logger):
    ack()
    view_path = os.path.join("block_kit", "conversation_modal.json")
    with open(view_path, 'r') as file:
        conversation_modal = json.load(file)
    
    trigger_id = body["trigger_id"]
    client.views_open(trigger_id=trigger_id, view=conversation_modal)