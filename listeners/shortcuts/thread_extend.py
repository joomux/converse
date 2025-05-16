from logging import Logger
from slack_bolt import Ack, Say
from slack_sdk import WebClient
import os
import json
from utils import threads, channel, helper

def extend_thread_callback(ack: Ack, shortcut: dict, client: WebClient, say: Say, logger: Logger):
    try:

        if "thread_ts" in shortcut:
            # if it's a reply, get the parent message ts
            main_ts = shortcut["thread_ts"]
        else:
            main_ts = shortcut["message_ts"]
        
        # say("Extending thread!")

        # logger.info("SHORTCUT")
        # logger.info(shortcut)
        channel_id = shortcut["channel"]["id"]

        if not channel.is_bot_in_channel(
            client=client,
            channel_id=channel_id
        ): 
            # now that 
            channel_info = channel.get_info(
                client=client,
                channel_id=channel_id
            )
            logger.info(channel_info)
            if channel_info and not channel_info["is_private"]:
                channel.add_bot_to_channel(
                    client=client,
                    channel_id=channel_id
                )
            else:
                # unable to add bot to channel!
                bot = client.auth_test()
                error = f"Unable to add <@{bot['user_id']}> to <#{channel_id}>. If this is a private channel, please manually add <@{bot['user_id']}> then try again."
                # client.chat_postEphemeral(channel=channel_id, user=body["user"]["id"], text=error)
                logger.error(error)
                view_path = os.path.join("block_kit", "error_modal.json")
                with open(view_path, 'r') as file:
                    error_modal = json.load(file)
                error_data = {
                    "title": "An error has occurred",
                    "error": error
                }
                rendered = helper.render_block_kit(template=error_modal, data=error_data)
                # return ack(response_action="errors", view=rendered)
                ack()
                return client.views_open(trigger_id=shortcut["trigger_id"], view=rendered)

        ack()
        # TODO: this needs to call the common extend_thread function, yet to be placed
        # conversation.extend_thread(client, shortcut["user"]["id"], shortcut["channel"]["id"], main_ts)
        threads.extend_thread(
            client=client, 
            member_id=shortcut["user"]["id"], 
            channel_id=shortcut["channel"]["id"], 
            message_ts=main_ts, 
            say=say, 
            logger=logger
        )

    except Exception as e:
        logger.error(e)