from logging import Logger
from slack_bolt import Ack, Say
from slack_sdk import WebClient
from utils import threads

def extend_thread_callback(ack: Ack, shortcut: dict, client: WebClient, say: Say, logger: Logger):
    try:
        ack()

        if "thread_ts" in shortcut:
            # if it's a reply, get the parent message ts
            main_ts = shortcut["thread_ts"]
        else:
            main_ts = shortcut["message_ts"]
        
        # say("Extending thread!")

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