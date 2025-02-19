from logging import Logger
from slack_sdk import WebClient
from slack_bolt import Say
from utils import threads

def app_mentioned_callback(event: dict, client: WebClient, logger: Logger, say: Say):
    logger.debug("EVENT APP MENTIONED!")

    # say("Hi! Thanks for the mention. Time to extend the thread!")
    # conversation.extend_thread(client, member_id=member_id, channel_id=channel_id, message_ts=message_ts)
    threads.extend_thread(
        client=client, 
        member_id=event["user"],
        channel_id=event["channel"], 
        message_ts=event["ts"], 
        say=say, 
        logger=logger
    )