from logging import Logger
from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError
from slack_bolt import Ack
# from utils.database import Database, DatabaseConfig
from ai import devxp
import os, json

def ai_designer(ack: Ack, body, client: WebClient, logger: Logger):
    logger.info("ABOUT TO DESIGN THE CHANNEL WITH AI!")
    ack()

    view_id = body["view"]["id"]
    view_path = os.path.join("block_kit", "loading.json")
    with open(view_path, 'r') as file:
        loading_modal = json.load(file)
    client.views_update(view_id=view_id, view=loading_modal)
    # client.views_push(trigger_id=body["trigger_id"], view=loading_modal)
    # need to get the channel info then pass it over to an AI prompt to get parameters back
    
    logger.info("AI DEISGNER")
    logger.debug(body)

    # test parameters
    # channel_name = "#proj-ai-designer" # get this from the private_metadata
    channel_id = body["view"]["private_metadata"]
    channel_info = client.conversations_info(channel=channel_id)
    logger.info(f"CHANNEL INFO: {channel_info}")
    channel_name = channel_info["channel"]["name"]
    channel_topic = body["view"]["state"]["values"]["channel_topic"]["channel_topic_input"]["value"] #"Figuring out how to design a Slack channel with AI"
    channel_description = body["view"]["state"]["values"]["channel_description"]["channel_description_input"]["value"] #"Conversations about using the internal DevXP AI LLM to build a set of parameters that can be used to design content for a Slack channel."

    params = devxp.design_channel(
        channel_name=channel_name,
        channel_topic=channel_topic,
        channel_description=channel_description
    )

    logger.debug(f"AI channel designer received input params: {params}")

    # Now update the form inputs with the received parameters

    view_path = os.path.join("block_kit", "conversation_modal.json")
    with open(view_path, 'r') as file:
        conversation_modal = json.load(file)


    conversation_modal["private_metadata"] = channel_id

    
    for block in conversation_modal["blocks"]: 
        # do we have a matching param based on block_id?
        if block.get("block_id") in params:
            logger.debug(f"Match on block_id in params. Working with \"{block.get('block_id')}\"")
            # we have a value!
            # now we need to format it correctly based on the input type
            if "accessory" in block:
                logger.debug(f"Ok, now we have an accessory of type: {block['accessory']['type']}")
                if "static_select" in block["accessory"]["type"]:
                    logger.info(f"--SETTING {block['block_id']} to {params[block['block_id']]}")
                    block["accessory"]["initial_option"] = get_option_from_value(block["accessory"]["options"], params[block["block_id"]])
            elif "element" in block:
                if "plain_text_input" in block["element"]["type"]:
                    content = params[block["block_id"]]
                    if isinstance(content, list):
                        content = ", ".join(content)
                    block["element"]["initial_value"] = content
        elif block.get("block_id") == "channel_topic" and channel_topic is not None:
            block["element"]["initial_value"] = channel_topic
            if len(channel_topic) > 150:
                    channel_topic = channel_topic[:147] + "..."
            block["element"]["placeholder"] = {"type": "plain_text", "text": channel_topic}
        elif block.get("block_id") == "channel_description" and channel_description is not None:
            block["element"]["initial_value"] = channel_description
            if len(channel_description) > 150:
                channel_description = channel_description[:147] + "..."
            block["element"]["placeholder"] = {"type": "plain_text", "text": channel_description}
        else:
            continue
            
    
    # conversation_modal["blocks"] = new_blocks
    logger.debug("UPDATED MODAL")
    logger.debug(conversation_modal)
    client.views_update(view_id=view_id, view=conversation_modal)


def get_option_from_value(options: list, value: str):
    for opt in options:
        if opt["value"] == value:
            return opt
        
    return value