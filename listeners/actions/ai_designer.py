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
    # need to get the channel info then pass it over to an AI prompt to get parameters back
    
    logger.debug(body)

    # test parameters
    channel_name = "#proj-ai-designer" # get this from the private_metadata
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
    
    
    # loop over the params and update the current value for the matching block_id item
    # blocks = conversation_modal["blocks"]
    # new_blocks = []
    # for block_id, value in params.items():
    #     for block in blocks:
    #         if block.get("block_id") == block_id:
    #             if "accessory" in block:
    #                 if "static_select" in block["accessory"]:
    #                     for option in block["accessory"]["options"]:
    #                         if option["value"] == value:
    #                             block["accessory"].set("initial_option", option)
    #                             break
    #                 elif "multi_static_select" in block["accessory"]:
    #                     selected_options = [option for option in block["accessory"]["options"] if option["value"] in value.split(",")]
    #                     block["accessory"].set("initial_options", selected_options)
    #             elif "element" in block:
    #                 if "plain_text_input" in block["element"]:
    #                     block["element"].set("initial_value", value)
    #             break
    #     new_blocks.append(block)

    
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
                    block["element"]["initial_value"] = params[block["block_id"]]
                pass
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