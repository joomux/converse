import os
import json
from utils import builder
from logging import Logger
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from utils.database import Database, DatabaseConfig
from listeners.actions import builder
from utils import builder as util_builder # avoid conflicts

db = Database(DatabaseConfig())

def app_home_opened_callback(client: WebClient, event: dict, logger: Logger):
    try:
        # Fetch builder options from the database for this user
        user_id = event["user"]
        
        # Get the team ID from the client's auth test
        auth_test = client.auth_test()
        app_installed_team_id = auth_test["team_id"]
        
        query = "SELECT mode FROM user_builder_selections WHERE user_id = %s AND app_installed_team_id = %s"
        result = db.fetch_one(query, (user_id, app_installed_team_id))

        mode = result["mode"] if result else None
        logger.info(f"Query result for user {user_id} in team {app_installed_team_id}: {mode}")
    
        if mode == "builder":
            # User is in builder mode, show builder view
            builder.update_app_home_to_builder_mode(client, user_id, app_installed_team_id, logger=logger)

        else:

            # Retrieve the builder options from the database
            builder_options = util_builder.get_user_selections(user_id, app_installed_team_id, logger=logger)  

            # Path to home_tab.json Block Kit template
            file_path = os.path.join("block_kit", "home_tab.json")
            
            # Read the home tab view JSON from the file
            with open(file_path, "r") as file:
                view = json.load(file)

            # # Mapping dictionary
            # option_mapping = {
            #     "option-convo":"*Conversations*",
            #     "option-channels": "*Channels*",
            #     "option-canvas": "*Canvas*",
            #     "option-apps": "*Apps*"
            # }

            # # Modify the Block Kit JSON to display builder options
            # if builder_options:
            #     selected_options = builder_options.get('save_builder_config', [])

            #     # Map the selected values to their display names
            #     display_values = [option_mapping.get(value, value) for value in selected_options]
                    
            #     if display_values:
            #         # Format the selected options into a string
            #         options_str = ", ".join(display_values)
            #         # Update the Block Kit view with the selected options
            #         view["blocks"][3]["elements"] = [
            #             {
            #                 "type": "mrkdwn",
            #                 "text": f"Demo components currently configured: {options_str}"
            #             }
            #         ]
            #     else:
            #         # Display a message when no options are selected
            #         view["blocks"][3]["elements"] = [
            #             {
            #                 "type": "mrkdwn",
            #                 "text": ":no_entry_sign: Demo components currently configured: *No selections.*"
            #             }
            #         ]
            # else:
            #     # Handle case where there are no builder options in the database
            #     view["blocks"][3]["elements"] = [
            #         {
            #             "type": "mrkdwn",
            #             "text": ":no_entry_sign: Demo components currently configured: *No selections.*"
            #         }
            #     ]

            # Publish the updated view to the Slack app home
            client.views_publish(
                user_id=event["user"],  # User ID from the event
                view={
                        "type": "home",
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": "*Welcome home, <@" + event["user"] + "> :house:*"
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                "type": "mrkdwn",
                                "text": "Learn how home tabs can be more useful and interactive <https://docs.slack.dev/surfaces/app-home|*in the documentation*>."
                                }
                            }
                        ]
                    }
            )
            
            # Log the successful update
            logger.info(f"Home tab updated for user {user_id}")

    except Exception as e:
        logger.error(f"Error updating home tab: {e}")


