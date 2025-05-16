import os
from logging import Logger
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging

logging.basicConfig(level=os.environ.get('LOGLEVEL', logging.DEBUG))
logger = logging.getLogger(__name__)

def is_bot_in_channel(client: WebClient, channel_id: str):
    logger.info("Checking if bot is in the channel")
    try:
        members_response = client.conversations_members(channel=channel_id)
        member_ids = members_response["members"]

        # Get bot's own user ID
        bot_info = client.auth_test()
        bot_user_id = bot_info["user_id"]

        return bot_user_id in member_ids
        
    except Exception as e:
        logger.error(f"Error checking/joining channel {channel_id}: {e}")
        return False

def add_bot_to_channel(client: WebClient, channel_id: str):
    logger.info("Adding bot to channel")
    try:
        result = client.conversations_join(channel=channel_id)

        return result["ok"]
    except Exception as e:
        logger.error(f"Error adding bot to channel {channel_id}: {e}")
        raise

def get_info(client: WebClient, channel_id: str):
    logger.info("Getting channel info")
    try:
        info = client.conversations_info(
            channel=channel_id,
            include_num_members=True
        )
        if info["ok"]:
            return info["channel"]
    except Exception as e:
        logger.error(f"Error getting channel info: {e}")
        # raise
    return False

def get_users(client: WebClient, channel_id: str, exclude_bots: bool = True):
    logger.info("Getting users")
    try:
        info = get_info(
            client=client,
            channel_id=channel_id
        )
        members = client.conversations_members(
            channel=channel_id,
            limit=info["num_members"]
        )

        member_list = []
        for member_id in members["members"]:
            member_info = client.users_info(user=member_id)["user"]
            if exclude_bots and member_info["is_bot"]:
                continue
            member_list.append(member_info)
        return member_list
    except Exception as e:
        logger.error(f"Error getting channel members: {e}")
        raise

def set_purpose(client: WebClient, channel_id: str, purpose: str):
    logger.info("Setting channel purpose")
    try:
        response = client.conversations_setPurpose(
            channel=channel_id,
            purpose=purpose
        )
        return response["ok"]
    except SlackApiError as e:
        logger.error(f"Failed to set channel purpose: {e}")
        return False

def set_topic(client: WebClient, channel_id: str, topic: str):
    logger.info("Setting channel topic")
    try:
        response = client.conversations_setTopic(
            channel=channel_id,
            topic=topic
        )
        return response["ok"]
    except SlackApiError as e:
        logger.error(f"Failed to set channel purpose: {e}")
        return False
