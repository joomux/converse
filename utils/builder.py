import os
import json
from logging import Logger
from slack_sdk import WebClient
from utils.database import Database, DatabaseConfig
from datetime import datetime, timezone

db = Database(DatabaseConfig())

# Retrieve "builder mode" users selections
def get_user_selections(user_id, app_installed_team_id, logger: Logger):
    try:
        # query = text("SELECT builder_options FROM user_builder_selections WHERE user_id = :user_id AND app_installed_team_id = :app_installed_team_id")
        # with engine.connect() as conn:
        #     result = conn.execute(query, {"user_id": user_id, "app_installed_team_id": app_installed_team_id}).fetchone()
        result = db.fetch_one("SELECT builder_options FROM user_builder_selections WHERE user_id = %s AND app_installed_team_id = %s", (user_id, app_installed_team_id))
        logger.info(f"Query result for user {user_id} in team {app_installed_team_id}: {result}")
        if result and result["builder_options"]:
            return result["builder_options"]
        return {}
    except Exception as e:
        logger.error(f"Error getting user selections: {e}")
        return None

def save_user_selections(user_id, app_installed_team_id, selections, logger: Logger):
    try:
        db.upsert(
            table="user_builder_selections", 
            data={
                "user_id": user_id,
                "builder_options": json.dumps(selections),  # Convert selections to JSON string
                "last_updated": datetime.now(timezone.utc),  # Use timezone-aware datetime
                "app_installed_team_id": app_installed_team_id,
                "mode": "builder"
            },
            where={"user_id": user_id}
        )
        logger.debug(f"Successfully saved selections for user_id {user_id}")
    except Exception as e:
        logger.error(f"Error saving builder mode selections and mode: {e}")