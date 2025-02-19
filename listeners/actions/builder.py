import os
import json
from utils import builder
from logging import Logger
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import Ack
from utils.database import Database, DatabaseConfig
from utils import user
from datetime import datetime, timezone
from listeners.events import app_home_opened

db = Database(DatabaseConfig())


def handle_enter_builder_mode(ack: Ack, body, client: WebClient, mode, logger: Logger):
    ack()
    try:
        # Extract app_installed_team_id
        app_installed_team_id = body["view"].get("app_installed_team_id")

        user_id = body["user"]["id"]

        # query = text("""
        #     UPDATE user_builder_selections 
        #     SET mode = 'builder', last_updated = :last_updated
        #     WHERE user_id = :user_id AND app_installed_team_id = :app_installed_team_id
        # """)
        
        # with engine.connect() as conn:
        #     conn.execute(query, {
        #         "user_id": user_id,
        #         "app_installed_team_id": app_installed_team_id,
        #         "mode": mode,
        #         "last_updated": datetime.now(timezone.utc)
        #     })
        
        db.update(
            "user_builder_selections", 
            {"mode": 'builder', "last_updated": datetime.now(timezone.utc)},
            {"user_id": user_id, "app_installed_team_id": app_installed_team_id})
        logger.debug(f"Successfully updated mode to {mode} for user_id {user_id}")
        
        # Update the App Home
        update_app_home_to_builder_mode(client, body["user"]["id"], app_installed_team_id, logger=logger)
    except Exception as e:
        logger.error(f"Error updating App Home to builder mode: {e}")


def update_app_home_to_builder_mode(client, user_id, app_installed_team_id, logger: Logger):
    # Load the builder mode view JSON
    view_path = os.path.join("block_kit", "builder_mode.json")
    with open(view_path, "r") as file:
        builder_view = json.load(file)

    # Retrieve user selections from the database, passing app_installed_team_id
    builder_options = builder.get_user_selections(user_id, app_installed_team_id, logger=logger)  # Pass the app_installed_team_id here

    # If selections are available, update the builder view with the selected options
    if builder_options:
        selected_values = builder_options.get("save_builder_config", [])
  
        # Loop through blocks and update multi_static_select
        for block in builder_view["blocks"]:
            if "accessory" in block and block["accessory"].get("type") == "multi_static_select":
                accessory = block["accessory"]
                if selected_values:
                    # Filter the options based on selected values, add them to initial_options
                    accessory["initial_options"] = [
                        option for option in accessory["options"] if option["value"] in selected_values
                    ]
                else:
                    # Remove initial_options if no options are selected
                    if "initial_options" in accessory:
                        del accessory["initial_options"]
   
        # Check if "Conversations" is selected and add additional Block Kit elements
        if "option-convo" in selected_values:
            # Append blocks for conversations
            convo_divider_block = {
                "type": "divider"
            }
    
            convo_title_block = {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Conversations"
                }
		    }

            convo_button_block = { 
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Configure"
                        },
                        "value": "setup-convo",
                        "action_id": "setup-convo"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":sparkles: Generate"
                        },
                        "style": "primary",
                        "value": "generate-convo",
                        "action_id": "generate-convo"
                    }
                ]
            }
            builder_view["blocks"].append(convo_divider_block)
            builder_view["blocks"].append(convo_title_block)
            builder_view["blocks"].append(convo_button_block)
            logger.debug("Added additional block for Conversations")

        # Check if "Channels" is selected and add additional Block Kit elements
        if "option-channels" in selected_values:
            channels_divider_block = {
                "type": "divider"
            }
    
            channels_title_block = {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Channels"
                }
		    }

            channels_button_block = { 
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Configure"
                        },
                        "value": "setup-channels",
                        "action_id": "setup-channels"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":sparkles: Generate"
                        },
                        "style": "primary",
                        "value": "generate-channels",
                        "action_id": "generate-channels"
                    }
                ]
            }
            builder_view["blocks"].append(channels_divider_block)
            builder_view["blocks"].append(channels_title_block)
            builder_view["blocks"].append(channels_button_block)
            logger.debug("Added additional block for Channels")

        # Check if "Canvas" is selected and add additional Block Kit elements
        if "option-canvas" in selected_values:
            canvas_divider_block = {
                "type": "divider"
            }
    
            canvas_title_block = {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Canvas"
                }
		    }

            canvas_button_block = {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Configure"
                        },
                        "value": "setup-canvas",
                        "action_id": "setup-canvas"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":sparkles: Generate"
                        },
                        "style": "primary",
                        "value": "generate-canvas",
                        "action_id": "generate-canvas"
                    }
                ]
            }
            builder_view["blocks"].append(canvas_divider_block)
            builder_view["blocks"].append(canvas_title_block)
            builder_view["blocks"].append(canvas_button_block)
            logger.debug("Added additional block for Canvas")

        # Check if "Apps" is selected and add additional Block Kit elements
        if "option-apps" in selected_values:
                apps_divider_block = {
                    "type": "divider"
                }
        
                apps_title_block = {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Apps"
                    }
                }

                apps_button_block = {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Configure"
                            },
                            "value": "setup-apps",
                            "action_id": "setup-apps"
                        },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": ":sparkles: Generate"
                        },
                        "style": "primary",
                        "value": "generate-apps",
                        "action_id": "generate-apps"
                    }
                    ]
                }
                builder_view["blocks"].append(apps_divider_block)
                builder_view["blocks"].append(apps_title_block)
                builder_view["blocks"].append(apps_button_block)
                logger.debug("Added additional block for Apps")


    # Log the modified builder view JSON
    logger.debug(f"Modified builder view JSON: {json.dumps(builder_view, indent=2)}")

    # Update the App Home with the modified builder view
    try:
        client.views_publish(
            user_id=user_id,
            view=builder_view
        )
    except SlackApiError as e:
        logger.error(f"Error updating App Home: {e}")


def save_builder_config(ack: Ack, body: dict, client: WebClient, logger: Logger):
    ack()
    try:
        # Get user ID and selections
        user_id = body.get("user", {}).get("id")
        app_installed_team_id = body.get("view", {}).get("app_installed_team_id")
        selections = body.get("view", {}).get("state", {}).get("values", {})
        app_installed_team_id = body.get("view", {}).get("app_installed_team_id")

        if user_id is None:
            logger.error("User ID not found in the request body")
            return  # or handle this error case appropriately

        if app_installed_team_id is None:
            logger.error("app_installed_team_id not found in the request body")
            return  # or handle this error case appropriately

        if not selections:
            logger.error("No selections found in the request body")
            return  # or handle this error case appropriately

        # Extract specific IDs or values from the selections
        selected_values = {}
        for block_id, block in selections.items():
            for action_id, action in block.items():
                if action["type"] == "multi_static_select":
                    selected_values[action_id] = [option["value"] for option in action["selected_options"]]

        # Save the selections to the database
        builder.save_user_selections(user_id, app_installed_team_id, selected_values, logger=logger)
        
        # Log the successful save
        logger.info(f"Successfully saved selections for user {user_id}")
        
        # Reload the builder mode app view
        update_app_home_to_builder_mode(client, user_id, app_installed_team_id, logger=logger)
    except Exception as e:
        logger.error(f"Error saving builder mode selections: {e}")

def save_exit_builder_mode(ack: Ack, body, client: WebClient, mode, logger: Logger):
    ack()
    try:
        # Log the entire body for debugging
        #logger.debug(f"Received body in save_exit_builder_mode: {json.dumps(body, indent=2)}")

        # Extract app_installed_team_id safely
        app_installed_team_id = body.get("view", {}).get("app_installed_team_id")

        if not app_installed_team_id:
            logger.error("app_installed_team_id not found in body")
            return
        
        # Extract user ID safely
        user_id = body.get("user", {}).get("id")
        
        if not user_id:
            logger.error("User ID not found in body")
            return
        
        # Create an event-like dictionary for update_home_tab
        event = {
            "user": user_id,
            "view": {"app_installed_team_id": app_installed_team_id}
        }

        # query = text("""
        #     UPDATE user_builder_selections 
        #     SET mode = 'home', last_updated = :last_updated
        #     WHERE user_id = :user_id AND app_installed_team_id = :app_installed_team_id
        # """)
        
        # with engine.connect() as conn:
        #     conn.execute(query, {
        #         "user_id": user_id,
        #         "app_installed_team_id": app_installed_team_id,
        #         "mode": mode,
        #         "last_updated": datetime.now(timezone.utc)
        #     })
        db.update(
            "user_builder_selections", 
            {"mode": 'home', "last_updated": datetime.now(timezone.utc)},
            {"user_id": user_id, "app_installed_team_id": app_installed_team_id}
        )
        logger.debug(f"Successfully updated mode to {mode} for user_id {user_id}")

        # Call update_home_tab with the correct parameters
        # update_home_tab(client, event, logger)
        app_home_opened.app_home_opened_callback(client, event, logger)
    except Exception as e:
        logger.error(f"Error exiting builder mode: {e}")