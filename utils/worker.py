from slack_bolt import App
from slack_sdk.errors import SlackApiError
import logging
import time
from .database import Database, DatabaseConfig
from typing import Dict, Any

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

db = Database(DatabaseConfig())

def get_user(client, member_id: str):
    # do database lookups and stuff!
    temp_user = db.fetch_one("SELECT id, api_key, member_id, team_id, enterprise_id, date_updated FROM users WHERE member_id = %s", (member_id,))
    logger.debug(f"TEMP USER FROM DB {temp_user}")

    # if no match, create one then call get_user again
    if temp_user and "id" in temp_user:
        return temp_user
    else: # no user found!
        # fetch the user to get the enterprise id
        temp_user = get_user_info(client, member_id=member_id)

        logger.debug(f"TEMP USER FROM USER INFO: {temp_user}")

        # TODO: was going to generate an API key here, but I don't think it's needed anymore with moving workflows into the app

        ent_id = temp_user["user"]["enterprise_user"]["enterprise_id"]

        user = {
            "member_id": member_id,
            "team_id": temp_user["team_id"],
            "enterprise_id": ent_id
        }

        user = db.insert("users", user)
        return get_user(client, member_id)

def get_user_info(client, member_id: str):
    try:
        user = client.users_info(user=member_id)
        return user
    except SlackApiError as e:
        logger.error(f"Error fetching user info: {e}")

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

def get_time(as_milli: bool = True):
    now = time.time()
    return round(now*1000) if as_milli else now