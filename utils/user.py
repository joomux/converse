from logging import Logger
from slack_sdk.errors import SlackApiError
from utils.database import Database, DatabaseConfig
import time

db = Database(DatabaseConfig())

def get_user(client, member_id: str, logger: Logger):
    # do database lookups and stuff!
    temp_user = db.fetch_one("SELECT id, api_key, member_id, team_id, enterprise_id, date_updated FROM users WHERE member_id = %s", (member_id,))
    logger.debug(f"TEMP USER FROM DB {temp_user}")

    # if no match, create one then call get_user again
    if temp_user and "id" in temp_user:
        return temp_user
    else: # no user found!
        # fetch the user to get the enterprise id
        temp_user = get_user_info(client, member_id=member_id, logger=logger)

        logger.debug(f"TEMP USER FROM USER INFO: {temp_user}")

        # TODO: was going to generate an API key here, but I don't think it's needed anymore with moving workflows into the app

        ent_id = temp_user["user"]["enterprise_user"]["enterprise_id"]

        user = {
            "member_id": member_id,
            "team_id": temp_user["team_id"],
            "enterprise_id": ent_id
        }

        user = db.insert("users", user)
        return get_user(client, member_id, logger=logger)
    

def get_user_info(client, member_id: str, logger: Logger):
    try:
        user = client.users_info(user=member_id)
        return user
    except SlackApiError as e:
        logger.error(f"Error fetching user info: {e}")

def get_time(as_milli: bool = True):
    now = time.time()
    return round(now*1000) if as_milli else now