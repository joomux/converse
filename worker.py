from slack_bolt import App, Ack, Fail, Complete, Say
from slack_sdk.errors import SlackApiError
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_channel_members(client, channel):
    # Get channel members
    try:
        # channel_info = client.conversations_info(channel=channel)
        members = client.conversations_members(channel=channel)["members"]

        bot_info = client.auth_test()
        bot_user_id = bot_info["user_id"]
        # If bot is not a member
        if bot_user_id not in members:
            # Check if channel is private
            client.conversations_join(channel=channel)
        
        # member_ids = members["members"]

        # Get info for each member to filter out bots
        human_members = []
        for member_id in members:
            try:
                member_info = client.users_info(user=member_id)
                if not member_info["user"]["is_bot"]:
                    human_members.append(member_id)
            except Exception as e:
                logger.error(f"Error getting info for member {member_id}: {e}")
                continue
        return human_members
    except SlackApiError as e:
        
        return
    except Exception as e:
        logger.error(f"Error checking channel membership: {e}")
        raise

def _get_user_by_name(name: str):
    pass