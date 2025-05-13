from logging import Logger
from slack_bolt import Ack, Say
from slack_sdk import WebClient
from utils import threads, channel

def extend_thread_callback(ack: Ack, shortcut: dict, client: WebClient, say: Say, logger: Logger):
    try:
        ack()

        if "thread_ts" in shortcut:
            # if it's a reply, get the parent message ts
            main_ts = shortcut["thread_ts"]
        else:
            main_ts = shortcut["message_ts"]
        
        # say("Extending thread!")

        # logger.info("SHORTCUT")
        # logger.info(shortcut)
        channel_id = shortcut["channel"]["id"]
        channel_info = channel.get_info(
            client=client,
            channel_id=channel_id
        )

        if not channel.is_bot_in_channel(client=client, channel_id=channel_id):
            if not channel_info["is_private"]:
                channel.add_bot_to_channel(
                    client=client,
                    channel_id=channel_id
                )
            else:
                # unable to add bot to channel!
                error = f"Unable to add Converse to <#{channel_id}>. If this is a private channel, please manually add Converse then try again."
                say(error)
                logger.error(error)
                raise

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