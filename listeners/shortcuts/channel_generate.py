import os
from logging import Logger
from slack_bolt import Ack, Say
from slack_sdk import WebClient
import json


def channel_generate_callback(ack: Ack, shortcut: dict, client: WebClient, say: Say, logger: Logger):
    ack()
    try:
        logger.info("SHORTCUT")
        logger.info(shortcut)
        view_path = os.path.join("block_kit", "add_conversation_channel_select_modal.json")
        with open(view_path, 'r') as file:
            conversation_modal = json.load(file)
        
        trigger_id = shortcut["trigger_id"]
        view = client.views_open(trigger_id=trigger_id, view=conversation_modal)
        logger.info(f"INITIAL VIEW ID: {view['view']['id']}") # V08QNQEUBU6 | V08QNQEUBU6
        # logger.info("RESPONSE START")
        # logger.info(view)
        # logger.info("RESPONSE END")

        # channel_id = view["view"]["blocks"]

        # target_channel_block = next((block for block in view["view"]["blocks"] if block.get("block_id") == "target_channel_id"), None)
        # if target_channel_block:
        #     logger.info("Target Channel Block found")
        #     # logger.info(target_channel_block)
        #     channel_id = target_channel_block["accessory"]["initial_conversation"]
        #     # logger.info(f"CHANNEL ID: {channel_id}")

        #     # Update the values of the view
        #     channel_info = client.conversations_info(channel=channel_id)
        #     # logger.info(f"CHANNEL INFO: {channel_info}")

        #     # Start Generation Here
        #     for block in conversation_modal["blocks"]:
        #         if block.get("block_id") == "channel_topic":
        #             block["element"]["placeholder"] = {"type": "plain_text", "text": channel_info["channel"]["topic"]["value"]}
        #             block["element"]["initial_value"] = channel_info["channel"]["topic"]["value"]
        #         if block.get("block_id") == "channel_description":
        #             block["element"]["placeholder"] = {"type": "plain_text", "text": channel_info["channel"]["purpose"]["value"]}
        #             block["element"]["initial_value"] = channel_info["channel"]["purpose"]["value"]

        #     # logger.info("CONTENT")
        #     # logger.info(conversation_modal)
        #     client.views_update(view_id=view["view"]["id"], view=conversation_modal)

        # else:
        #     logger.error("Target Channel Block not found")
    except Exception as e:
        logger.error(f"CHANNEL_GENERATE error: {e}")
