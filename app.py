from slack_bolt import App, Ack, Fail, Complete, Say
from slack_sdk.errors import SlackApiError
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
from dotenv import load_dotenv
import requests
import random
import json
import logging
import time
from datetime import datetime, timezone
import factory
import logistics
import worker
import conversation
from objects import Database, DatabaseConfig
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

db = Database(DatabaseConfig())

# Load environment variables
load_dotenv()

# Verify environment variables are present
required_env_vars = ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET", "SLACK_APP_TOKEN"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Initialize app with your bot token and signing secret
app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

# Add after other global variables
user_inputs = {}  # Dictionary to store user inputs

@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    try:
        # Fetch builder options from the database for this user
        user_id = event["user"]
        # Fetch team ID
        app_installed_team_id = event["view"]["app_installed_team_id"]

        # Retrieve the mode from the database
        # query = text("SELECT mode FROM user_builder_selections WHERE user_id = :user_id AND app_installed_team_id = :app_installed_team_id")
        # with engine.connect() as conn:
        #     result = conn.execute(query, {"user_id": user_id, "app_installed_team_id": app_installed_team_id}).fetchone()
        
        query = "SELECT mode FROM user_builder_selections WHERE user_id = %s AND app_installed_team_id = %s"
        result = db.fetch_one(query, (user_id, app_installed_team_id))

        
        mode = result[0] if result else None
        logger.info(f"Query result for user {user_id} in team {app_installed_team_id}: {mode}")
    
        if mode == "builder":
            # User is in builder mode, show builder view
            update_app_home_to_builder_mode(client, user_id, app_installed_team_id)

        else:

            # Retrieve the builder options from the database
            builder_options = get_user_selections(user_id, app_installed_team_id)  

            # Path to home_tab.json Block Kit template
            file_path = os.path.join("block_kit", "home_tab.json")
            
            # Read the home tab view JSON from the file
            with open(file_path, "r") as file:
                view = json.load(file)

            # Mapping dictionary
            option_mapping = {
                "option-convo":"*Conversations*",
                "option-channels": "*Channels*",
                "option-canvas": "*Canvas*",
                "option-apps": "*Apps*"
            }

            # Modify the Block Kit JSON to display builder options
            if builder_options:
                selected_options = builder_options.get('multi_static_select-action', [])

                # Map the selected values to their display names
                display_values = [option_mapping.get(value, value) for value in selected_options]
                    
                if display_values:
                    # Format the selected options into a string
                    options_str = ", ".join(display_values)
                    # Update the Block Kit view with the selected options
                    view["blocks"][3]["elements"] = [
                        {
                            "type": "mrkdwn",
                            "text": f"Demo components currently configured: {options_str}"
                        }
                    ]
                else:
                    # Display a message when no options are selected
                    view["blocks"][3]["elements"] = [
                        {
                            "type": "mrkdwn",
                            "text": ":no_entry_sign: Demo components currently configured: *No selections.*"
                        }
                    ]
            else:
                # Handle case where there are no builder options in the database
                view["blocks"][3]["elements"] = [
                    {
                        "type": "mrkdwn",
                        "text": ":no_entry_sign: Demo components currently configured: *No selections.*"
                    }
                ]

            # Publish the updated view to the Slack app home
            client.views_publish(
                user_id=event["user"],  # User ID from the event
                view=view
            )
            
            # Log the successful update
            logger.info(f"Home tab updated for user {user_id}")

    except Exception as e:
        logger.error(f"Error updating home tab: {e}")


@app.action("enter_builder_mode_button")
def handle_enter_builder_mode(ack, body, client, mode):
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
        update_app_home_to_builder_mode(client, body["user"]["id"], app_installed_team_id)
    except Exception as e:
        logger.error(f"Error updating App Home to builder mode: {e}")

def update_app_home_to_builder_mode(client, user_id, app_installed_team_id):
    # Load the builder mode view JSON
    view_path = os.path.join("block_kit", "builder_mode.json")
    with open(view_path, "r") as file:
        builder_view = json.load(file)

    # Retrieve user selections from the database, passing app_installed_team_id
    builder_options = get_user_selections(user_id, app_installed_team_id)  # Pass the app_installed_team_id here

    # If selections are available, update the builder view with the selected options
    if builder_options:
        selected_values = builder_options.get("multi_static_select-action", [])
  
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

@app.action("save_exit_builder_mode")
def handle_save_exit_builder_mode(ack, body, client, mode):
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
        update_home_tab(client, event, logger)
    except Exception as e:
        logger.error(f"Error exiting builder mode: {e}")


@app.action("multi_static_select-action")
def handle_some_action(ack, body, client, logger):
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
        save_user_selections(user_id, app_installed_team_id, selected_values)
        
        # Log the successful save
        logger.info(f"Successfully saved selections for user {user_id}")
        
        # Reload the builder mode app view
        update_app_home_to_builder_mode(client, user_id, app_installed_team_id)

    except Exception as e:
        logger.error(f"Error saving builder mode selections: {e}")

# Database connection and save "builder mode" selections
# DATABASE_URL = "postgresql://postgres:postgres@localhost/converse2"
# engine = create_engine(DATABASE_URL)

# def test_connection():
#     try:
#         with engine.connect() as connection:
#             logger.debug("Database connection successful!")
#             return True
#     except Exception as e:
#         logger.error(f"Failed to connect to the database: {e}")
#         return False

def save_user_selections(user_id, app_installed_team_id, selections):

    # if not test_connection():
    #     logger.error("Aborting: Unable to connect to the database.")
    #     return
    
    try:
        # query = text("""
        #     INSERT INTO user_builder_selections (user_id, builder_options, last_updated, app_installed_team_id)
        #     VALUES (:user_id, :builder_options, :last_updated, :app_installed_team_id)
        #     ON CONFLICT (user_id, app_installed_team_id) 
        #     DO UPDATE SET 
        #         builder_options = EXCLUDED.builder_options,
        #         last_updated = EXCLUDED.last_updated
        # """)
        # #logger.debug(f"Executing query for user_id {user_id}: {selections}")
        
        # with engine.connect() as conn:
        #     conn.execute(query, {
        #         "user_id": user_id,
        #         "builder_options": json.dumps(selections),  # Convert selections to JSON string
        #         "last_updated": datetime.now(timezone.utc),  # Use timezone-aware datetime
        #         "app_installed_team_id": app_installed_team_id
        #     })
        #     conn.commit()
        
        db.insert(
            "user_builder_selections", 
            {
                "user_id": user_id,
                "builder_options": json.dumps(selections),  # Convert selections to JSON string
                "last_updated": datetime.now(timezone.utc),  # Use timezone-aware datetime
                "app_installed_team_id": app_installed_team_id
            }
        )
        logger.debug(f"Successfully saved selections for user_id {user_id}")
    except Exception as e:
        logger.error(f"Error saving builder mode selections and mode: {e}")

# Retrieve "builder mode" users selections
def get_user_selections(user_id, app_installed_team_id):
    try:
        # query = text("SELECT builder_options FROM user_builder_selections WHERE user_id = :user_id AND app_installed_team_id = :app_installed_team_id")
        # with engine.connect() as conn:
        #     result = conn.execute(query, {"user_id": user_id, "app_installed_team_id": app_installed_team_id}).fetchone()
        result = db.fetch_one("SELECT builder_options FROM user_builder_options WHERE user_id = %s AND app_installed_team_id = %s", (user_id, app_installed_team_id))
        logger.info(f"Query result for user {user_id} in team {app_installed_team_id}: {result}")
        if result and result[0]:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Error getting user selections: {e}")
        return None



# @app.action("open_channel_creator")
# def handle_open_channel_creator(ack, body, client):
#     ack()
#     try:
#         # Get user ID and any stored values
#         user_id = body["user"]["id"]
#         stored_values = user_inputs.get(user_id, {})
        
#         # Open modal with form
#         client.views_open(
#             trigger_id=body["trigger_id"],
#             view={
#                 "type": "modal",
#                 "callback_id": "channel_creator_submission",
#                 "title": {
#                     "type": "plain_text",
#                     "text": "Channel Creator"
#                 },
#                 "submit": {
#                     "type": "plain_text",
#                     "text": "Generate Channels"
#                 },
#                 "blocks": [
#                     {
#                         "type": "input",
#                         "block_id": "customer_name_input",
#                         "element": {
#                             "type": "plain_text_input",
#                             "action_id": "customer_name",
#                             "initial_value": stored_values.get("customer_name", ""),
#                             "placeholder": {
#                                 "type": "plain_text",
#                                 "text": "Enter customer name..."
#                             }
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Customer Name"
#                         },
#                         "optional": True
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "use_case_input",
#                         "element": {
#                             "type": "plain_text_input",
#                             "action_id": "use_case",
#                             "initial_value": stored_values.get("use_case", ""),
#                             "placeholder": {
#                                 "type": "plain_text",
#                                 "text": "Describe your use case for channel creation..."
#                             },
#                             "multiline": True
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Use Case Description"
#                         }
#                     }
#                 ]
#             }
#         )
#     except Exception as e:
#         logger.error(f"Error opening channel creator modal: {e}")

@app.view("channel_creator_submission")
def handle_channel_creator_submission(ack, body, client, view, logger):
    ack()
    # Move the channel generation logic from handle_generate_channels here
    user_id = body["user"]["id"]
    try:
        state_values = view["state"]["values"]
        
        # Initialize user dict if it doesn't exist
        if user_id not in user_inputs:
            user_inputs[user_id] = {}
        
        # Get use case description (required)
        use_case = state_values.get("use_case_input", {}).get("use_case", {}).get("value")
        if not use_case:
            user_inputs[user_id]["use_case"] = ""
            raise ValueError("Use Case Description is required")
        
        user_inputs[user_id]["use_case"] = use_case
        
        # Get customer name (optional)
        customer_name = state_values.get("customer_name_input", {}).get("customer_name", {}).get("value")
        user_inputs[user_id]["customer_name"] = customer_name
        
        # Rest of your existing channel generation logic from handle_generate_channels...
        # Show loading modal
        view_modal = client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "title": {
                    "type": "plain_text",
                    "text": "Creating Channels"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "🔄 Generating channels based on your input...\nThis may take a few moments."
                        }
                    }
                ]
            }
        )

        try:

            channels_list = factory._fetch_channels(customer_name, use_case)
            created_channels = logistics._send_channels(client, user_id, channels_list)
                    
            # client.chat_postMessage(
            #     channel=user_id,
            #     text=f"✅ Created {len(created_channels)} channels:\n" + "\n".join([f"<#{channel_id}>" for channel_id in created_channels])
            # )
            logistics.send_message(
                client=client,
                selected_channel=user_id,
                post={"message":f"✅ Created {len(created_channels)} channels:\n" + "\n".join([f"<#{channel_id}>" for channel_id in created_channels])}
            )
            # Close loading modal
            client.views_update(
                view_id=view_modal["view"]["id"],
                view={"type": "modal", "title": {"type": "plain_text", "text": "Creating Channels"}, "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"✅ Created {len(created_channels)} channels:\n" + "\n".join([f"<#{channel_id}>" for channel_id in created_channels])
                            }
                        }
                    ]}
            )
        except Exception as e:
            logger.error(f"Error in channel creation: {e}")

    except Exception as e:
        logger.error(f"Error in channel creator submission: {e}")
        # client.chat_postMessage(
        #     channel=user_id,
        #     text=f"❌ Error creating channels: {str(e)}"
        # )
        logistics.send_message(
            client=client,
            selected_channel=user_id,
            post={"message": f"❌ Error creating channels: {str(e)}"}
        )
        client.views_update(
            view_id=view_modal["view"]["id"],
            view={"type": "modal", "title": {"type": "plain_text", "text": "Creating Channels"}, "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ Error creating channels: {str(e)}"
                        }
                    }
                ]}
        )

@app.action("generate_canvas")
def handle_generate_canvas(ack, body, client, logger):
    ack()
    try:
        selected_channel = body["actions"][0]["value"]
        logger.info(f"Generating canvas for channel: {selected_channel}")

        # Update the modal to show generation in progress
        client.views_update(
            view_id=body["container"]["view_id"],
            view={
                "type": "modal",
                "title": {
                    "type": "plain_text",
                    "text": "Generating Canvas"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"🎨 Generating canvas for <#{selected_channel}>...\nThis may take a few moments."
                        }
                    }
                ]
            }
        )

        # Get channel info
        try:
            channel_info = client.conversations_info(channel=selected_channel, include_num_members=True)
            channel_details = channel_info["channel"]
            
            # Extract relevant channel details
            channel_name = channel_details["name"]
            channel_topic = channel_details.get("topic", {}).get("value", "")
            channel_purpose = channel_details.get("purpose", {}).get("value", "")
            is_private = channel_details["is_private"]
            member_count = channel_details["num_members"]
            created_ts = channel_details["created"]

            if channel_details.get("properties", {}).get("canvas", False):
                logger.info(f"Channel {channel_name} already has a canvas")
                do_canvas_update = True
            else:
                do_canvas_update = False
            
            logger.info(f"Retrieved info for channel {channel_name}")
            logger.debug(f"Topic: {channel_topic}")
            logger.debug(f"Purpose: {channel_purpose}") 
            logger.debug(f"Is private: {is_private}")
            logger.debug(f"Member count: {member_count}")
            logger.debug(f"Created timestamp: {created_ts}")         

            # Get member list for the channel
            members_response = client.conversations_members(channel=selected_channel)
            member_ids = members_response["members"]

            # Check if bot is member of channel and join if not
            try:
                # Get bot's own user ID
                bot_info = client.auth_test()
                bot_user_id = bot_info["user_id"]
                
                # Check if bot is in members list
                if bot_user_id not in member_ids:
                    logger.info(f"Bot not in channel {channel_name}, joining now...")
                    client.conversations_join(channel=selected_channel)
                    logger.info(f"Successfully joined channel {channel_name}")
            except Exception as e:
                logger.error(f"Error checking/joining channel {channel_name}: {e}")
                raise
            
            # Get 5 random members (or fewer if channel has less than 5 members)
            sample_size = min(5, len(member_ids))
            random_members = random.sample(member_ids, sample_size)
            
            logger.debug(f"Selected random members: {random_members}")

            content = factory._fetch_canvas(
                channel_name=channel_name,
                channel_purpose=channel_purpose,
                channel_topic=channel_topic,
                member_list=random_members
            )

            logger.info(content)

            canvas_id = logistics._send_canvas(client, selected_channel, content, do_canvas_update)
            
            # Get canvas file info
            canvas_info = client.files_info(file=canvas_id)
            logger.info(f"Canvas file info: {canvas_info['file']}")
            
            # Extract permalink
            canvas_permalink = canvas_info["file"]["permalink"]
            logger.info(f"Canvas permalink: {canvas_permalink}")
            # Send DM to user about canvas creation/update
            # client.chat_postMessage(
            #     channel=body["user"]["id"],
            #     text=f"{'Updated' if do_canvas_update else 'Created'} canvas for <#{selected_channel}>\n" +
            #          f"View it here: <{canvas_permalink}|{content['title']}>"
            # )
            logistics.send_message(
                client=client,
                selected_channel=body["user"]["id"],
                post={"message":f"{'Updated' if do_canvas_update else 'Created'} canvas for <#{selected_channel}>\n" +
                     f"View it here: <{canvas_permalink}|{content['title']}>"}
            )

            # # After successful canvas generation, refresh the channel details modal
            # channel_info = client.conversations_info(channel=selected_channel, include_num_members=True)
            # channel = channel_info["channel"]
            # history = client.conversations_history(channel=selected_channel, limit=1)
            
            # Reopen the channel details modal with updated info
            handle_channel_selection(ack, {
                "trigger_id": body["trigger_id"],
                "actions": [{"selected_conversation": selected_channel}],
                "user": {"id": body["user"]["id"]},
                "container": {"view_id": body["container"]["view_id"]}
            }, client, logger, returner=True)

        except SlackApiError as e:
            logger.error(f"Error getting channel info: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in canvas generation/update: {e}")
            error_view = {
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ Error: Unable to generate/update canvas.\nDetails: {str(e)}"
                        }
                    }
                ]
            }
            client.views_publish(
                user_id=body["user"]["id"],
                view=error_view
            )
        
        update_home_tab(client, {"user": body["user"]["id"]}, logger)

    except Exception as e:
        logger.error(f"Error generating canvas: {e}")
        # Show error in the modal instead of home view
        client.views_update(
            view_id=body["container"]["view_id"],
            view={
                "type": "modal",
                "title": {
                    "type": "plain_text",
                    "text": "Error"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"❌ Error: Unable to generate canvas.\nDetails: {str(e)}"
                        }
                    }
                ]
            }
        )

# @app.action("selected_channel")
def handle_channel_selection(ack, body, client, logger, returner=False):
    if not returner:
        ack()
    try:
        # Get selected channel ID
        selected_channel = body["actions"][0]["selected_conversation"]

        # Get bot's own user ID and check membership
        bot_info = client.auth_test()
        bot_user_id = bot_info["user_id"]
        
        # Get channel members
        try:
            channel_info = client.conversations_info(channel=selected_channel)
            members = client.conversations_members(channel=selected_channel)["members"]
            # If bot is not a member
            if bot_user_id not in members:
                # Check if channel is private
                client.conversations_join(channel=selected_channel)
        except SlackApiError as e:
            logger.error(f"Error checking channel membership: {e}")
            client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "title": {
                        "type": "plain_text",
                        "text": "Access Error"
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "❌ Unable to access this private channel. Please add the bot to the channel first."
                            }
                        }
                    ]
                }
            )
            return
        except Exception as e:
            logger.error(f"Error checking channel membership: {e}")
            raise
        
        # Get channel info
        channel_info = client.conversations_info(channel=selected_channel, include_num_members=True)
        channel = channel_info["channel"]
        
        # Get last message
        history = client.conversations_history(channel=selected_channel, limit=1)
        last_message = history["messages"][0]["ts"] if history["messages"] else "No messages"
        
        # Format timestamps
        from datetime import datetime
        created_date = datetime.fromtimestamp(channel["created"]).strftime("%Y-%m-%d %H:%M:%S")
        last_message_date = datetime.fromtimestamp(float(last_message)).strftime("%Y-%m-%d %H:%M:%S") if last_message != "No messages" else "Never"
        
        
        view_data={
                "type": "modal",
                "title": {
                    "type": "plain_text",
                    "text": f"Channel Details"
                },
                "close": {
                    "type": "plain_text",
                    "text": "Close"
                },
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"#{channel['name']}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Type:*\n{'Private' if channel['is_private'] else 'Public'} Channel"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Members:*\n{channel['num_members']} members"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Created:*\n{created_date}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Last Message:*\n{last_message_date}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Purpose:*\n{channel.get('purpose', {}).get('value', 'No purpose set')}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Topic:*\n{channel.get('topic', {}).get('value', 'No topic set')}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Channel Canvas Status:*\n{'✅ Has Canvas' if channel.get('properties', {}).get('canvas', False) else '❌ No Canvas'}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Last Message:*\n{history['messages'][0]['text'] if history['messages'] else 'No messages yet'}"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Generate Canvas",
                                    "emoji": True
                                },
                                "action_id": "generate_canvas",
                                "value": selected_channel
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Generate Conversation",
                                    "emoji": True
                                },
                                "action_id": "generate_conversation",
                                "value": selected_channel
                            }
                        ]
                    }
                ]
            }
        
        if not returner:
            # Open modal with channel details
            client.views_open(
                trigger_id=body["trigger_id"],
                view=view_data
            )
        else:
            client.views_update(
                view_id=body["container"]["view_id"],
                view=view_data
            )
    except Exception as e:
        logger.error(f"Error handling channel selection: {e}")
        # Send error message as ephemeral message
        client.chat_postEphemeral(
            channel=body["container"]["channel_id"],
            user=body["user"]["id"],
            text=f"❌ Error: Unable to load channel details.\nDetails: {str(e)}"
        )

# @app.action("generate_conversation")
# def handle_generate_conversation(ack, body, client, logger):
#     ack()
#     try:
#         selected_channel = body["actions"][0]["value"]
#         logger.info(f"Generating conversation for channel: {selected_channel}")

#         # Get channel info
#         try:
#             channel_info = client.conversations_info(channel=selected_channel, include_num_members=True)
#             channel_details = channel_info["channel"]
            
#             # Extract relevant channel details
#             channel_name = channel_details["name"]
#             channel_topic = channel_details.get("topic", {}).get("value", "")
#             channel_purpose = channel_details.get("purpose", {}).get("value", "")
#             is_private = channel_details["is_private"]
#             member_count = channel_details["num_members"]
#             created_ts = channel_details["created"]
            
#             logger.info(f"Retrieved info for channel {channel_name}")
#             logger.debug(f"Topic: {channel_topic}")
#             logger.debug(f"Purpose: {channel_purpose}")
#             logger.debug(f"Is private: {is_private}")
#             logger.debug(f"Member count: {member_count}")
#             logger.debug(f"Created timestamp: {created_ts}")

#             # Get member list for the channel
#             members_response = client.conversations_members(channel=selected_channel)
#             member_ids = members_response["members"]

#         except Exception as e:
#             logger.error(f"Error getting channel info: {e}")
#             raise

#         # Update modal with form
#         client.views_update(
#             view_id=body["container"]["view_id"],
#             view={
#                 "type": "modal",
#                 "callback_id": "conversation_generator_modal",
#                 "title": {
#                     "type": "plain_text", 
#                     "text": "Generate Conversation"
#                 },
#                 "submit": {
#                     "type": "plain_text",
#                     "text": "Generate"
#                 },
#                 "private_metadata": selected_channel,
#                 "blocks": [
#                     {
#                         "type": "header",
#                         "text": {
#                             "type": "plain_text",
#                             "text": f"Building conversation for #{channel_name}",
#                             "emoji": True
#                         }
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "company_name",
#                         "optional": True,
#                         "element": {
#                             "type": "plain_text_input",
#                             "action_id": "company_name_input",
#                             "placeholder": {
#                                 "type": "plain_text",
#                                 "text": "Enter company name"
#                             }
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Company Name (Optional)"
#                         }
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "industry",
#                         "element": {
#                             "type": "static_select",
#                             "action_id": "industry_select",
#                             "placeholder": {
#                                 "type": "plain_text",
#                                 "text": "Select industry"
#                             },
#                             "options": [
#                                 {"text": {"type": "plain_text", "text": "Technology"}, "value": "technology"},
#                                 {"text": {"type": "plain_text", "text": "Healthcare"}, "value": "healthcare"},
#                                 {"text": {"type": "plain_text", "text": "Finance"}, "value": "finance"},
#                                 {"text": {"type": "plain_text", "text": "Manufacturing"}, "value": "manufacturing"},
#                                 {"text": {"type": "plain_text", "text": "Retail"}, "value": "retail"}
#                             ]
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Industry"
#                         }
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "topics",
#                         "optional": True,
#                         "element": {
#                             "type": "multi_static_select",
#                             "action_id": "topics_select",
#                             "placeholder": {
#                                 "type": "plain_text",
#                                 "text": "Select topics"
#                             },
#                             "options": [
#                                 {"text": {"type": "plain_text", "text": "Product Development"}, "value": "product"},
#                                 {"text": {"type": "plain_text", "text": "Marketing"}, "value": "marketing"},
#                                 {"text": {"type": "plain_text", "text": "Sales"}, "value": "sales"},
#                                 {"text": {"type": "plain_text", "text": "Customer Support"}, "value": "support"},
#                                 {"text": {"type": "plain_text", "text": "Engineering"}, "value": "engineering"}
#                             ]
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Choose Topics (Optional)"
#                         }
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "custom_prompt",
#                         "optional": True,
#                         "element": {
#                             "type": "plain_text_input",
#                             "action_id": "custom_prompt_input",
#                             "multiline": True,
#                             "placeholder": {
#                                 "type": "plain_text",
#                                 "text": "Enter any specific instructions for conversation generation"
#                             }
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Custom Prompt Instructions (Optional)"
#                         }
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "num_participants",
#                         "element": {
#                             "type": "static_select",
#                             "action_id": "participants_select",
#                             "options": [
#                                 {"text": {"type": "plain_text", "text": "2-3"}, "value": "2-3"},
#                                 {"text": {"type": "plain_text", "text": "4-6"}, "value": "4-6"},
#                                 {"text": {"type": "plain_text", "text": "7-10"}, "value": "7-10"},
#                                 {"text": {"type": "plain_text", "text": "11-15"}, "value": "11-15"}
#                             ]
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Number of Participants"
#                         }
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "num_posts",
#                         "element": {
#                             "type": "static_select",
#                             "action_id": "posts_select",
#                             "options": [
#                                 {"text": {"type": "plain_text", "text": "5-10"}, "value": "5-10"},
#                                 {"text": {"type": "plain_text", "text": "11-20"}, "value": "11-20"},
#                                 {"text": {"type": "plain_text", "text": "21-30"}, "value": "21-30"},
#                                 {"text": {"type": "plain_text", "text": "31-50"}, "value": "31-50"}
#                             ]
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Number of Channel Posts"
#                         }
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "post_length",
#                         "element": {
#                             "type": "static_select",
#                             "action_id": "length_select",
#                             "options": [
#                                 {"text": {"type": "plain_text", "text": "Short (1-2 sentences)"}, "value": "short"},
#                                 {"text": {"type": "plain_text", "text": "Medium (3-4 sentences)"}, "value": "medium"},
#                                 {"text": {"type": "plain_text", "text": "Long (5+ sentences)"}, "value": "long"}
#                             ]
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Approximate Length of Each Post"
#                         }
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "tone",
#                         "element": {
#                             "type": "static_select",
#                             "action_id": "tone_select",
#                             "options": [
#                                 {"text": {"type": "plain_text", "text": "Formal"}, "value": "formal"},
#                                 {"text": {"type": "plain_text", "text": "Casual"}, "value": "casual"},
#                                 {"text": {"type": "plain_text", "text": "Professional"}, "value": "professional"},
#                                 {"text": {"type": "plain_text", "text": "Technical"}, "value": "technical"},
#                                 {"text": {"type": "plain_text", "text": "Executive"}, "value": "executive"},
#                                 {"text": {"type": "plain_text", "text": "Legal"}, "value": "legal"}
#                             ]
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Tone of Conversation"
#                         }
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "emoji_density",
#                         "element": {
#                             "type": "static_select",
#                             "action_id": "emoji_select",
#                             "options": [
#                                 {"text": {"type": "plain_text", "text": "Few"}, "value": "few"},
#                                 {"text": {"type": "plain_text", "text": "Average"}, "value": "average"},
#                                 {"text": {"type": "plain_text", "text": "A Lot"}, "value": "lot"}
#                             ]
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Emoji Density"
#                         }
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "thread_replies",
#                         "element": {
#                             "type": "static_select",
#                             "action_id": "replies_select",
#                             "options": [
#                                 {"text": {"type": "plain_text", "text": "0-2 replies"}, "value": "0-2"},
#                                 {"text": {"type": "plain_text", "text": "3-5 replies"}, "value": "3-5"},
#                                 {"text": {"type": "plain_text", "text": "6-10 replies"}, "value": "6-10"},
#                                 {"text": {"type": "plain_text", "text": "11-15 replies"}, "value": "11+"}
#                             ]
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Approximate Thread Replies"
#                         }
#                     },
#                     {
#                         "type": "input",
#                         "block_id": "save_conversation",
#                         "element": {
#                             "type": "checkboxes",
#                             "action_id": "save_conversation_checkbox",
#                             "options": [
#                                 {
#                                     "text": {
#                                         "type": "plain_text",
#                                         "text": "Save Conversation Definition"
#                                     },
#                                     "value": "save_conversation",
#                                     "description": {
#                                         "type": "mrkdwn",
#                                         "text": "Enable re-use manually, or via Workflow? Saves the above values, not the generated conversation, so every run produces something new!"
#                                     }
#                                 }
#                             ]
#                         },
#                         "label": {
#                             "type": "plain_text",
#                             "text": "Save Conversation"
#                         }
#                     }
#                 ]
#             }
#         )

#     except Exception as e:
#         logger.error(f"Error generating conversation: {e}")
#         client.chat_postEphemeral(
#             channel=body["container"]["channel_id"],
#             user=body["user"]["id"],
#             text=f"❌ Error: Unable to generate conversation.\nDetails: {str(e)}"
#         )

@app.view("conversation_generator_modal")
def handle_conversation_generator_submission(ack, body, client, view, logger):
    ack()
    
    current_user = worker.get_user(client, body["user"]["id"])

    # Initialize original_view_info outside try block
    original_view_info = None
    try:
        # Extract all form values
        state_values = view["state"]["values"]
        
        # Get all input values
        company_name = state_values["company_name"]["company_name_input"]["value"]
        industry = state_values["industry"]["industry_select"]["selected_option"]["value"]
        topics = [option["value"] for option in state_values["topics"]["topics_select"].get("selected_options", [])]
        custom_prompt = state_values["custom_prompt"]["custom_prompt_input"].get("value", "")
        num_participants = state_values["num_participants"]["participants_select"]["selected_option"]["value"]
        num_posts = state_values["num_posts"]["posts_select"]["selected_option"]["value"]
        post_length = state_values["post_length"]["length_select"]["selected_option"]["value"]
        tone = state_values["tone"]["tone_select"]["selected_option"]["value"]
        emoji_density = state_values["emoji_density"]["emoji_select"]["selected_option"]["value"]
        thread_replies = state_values["thread_replies"]["replies_select"]["selected_option"]["value"]
        # Get selected channel from private metadata
        selected_channel = view["private_metadata"]
        logger.debug(f"Selected channel for conversation generation: {selected_channel}")

        # Prep the message history log
        history_entry = {
            "conversation_id": None,
            "channel_id": selected_channel,
            "user_id": current_user["id"]
        }
        history_row = db.insert("history", history_entry)
        start_time = worker.get_time()

        # Build data dictionary from form values
        data = {
            "company_name": company_name,
            "industry": industry,
            "topics": topics,
            "custom_prompt": custom_prompt,
            "num_participants": num_participants,
            "num_posts": num_posts,
            "post_length": post_length,
            "tone": tone,
            "emoji_density": emoji_density,
            "thread_replies": thread_replies
        }

        view_body = _get_conversation_progress_view(data=data, total=10, current=0)

        # Show loading state
        original_view_info = client.views_open(
            trigger_id=body["trigger_id"],
            view=view_body
        )

        # Get channel info
        try:
            channel_info = client.conversations_info(channel=selected_channel, include_num_members=True)
            channel_details = channel_info["channel"]
            
            # Extract relevant channel details
            channel_name = channel_details["name"]
            channel_topic = channel_details.get("topic", {}).get("value", "")
            channel_purpose = channel_details.get("purpose", {}).get("value", "")
            is_private = channel_details["is_private"]
            member_count = channel_details["num_members"]
            created_ts = channel_details["created"]
            
            logger.info(f"Retrieved info for channel {channel_name}")
            logger.debug(f"Topic: {channel_topic}")
            logger.debug(f"Purpose: {channel_purpose}")
            logger.debug(f"Is private: {is_private}")
            logger.debug(f"Member count: {member_count}")
            logger.debug(f"Created timestamp: {created_ts}")

        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            raise

        # TODO: Add your conversation generation logic here
        # This is where you would call your AI service or other generation method
        # Get member list for the channel
        members_response = client.conversations_members(channel=selected_channel)
        member_ids = members_response["members"]

        # Get info for each member to filter out bots
        human_members = []
        for member_id in member_ids:
            try:
                member_info = client.users_info(user=member_id)
                if not member_info["user"]["is_bot"]:
                    human_members.append(member_id)
            except Exception as e:
                logger.error(f"Error getting info for member {member_id}: {e}")
                continue

        # Extract max number from range (e.g., "2-3" becomes 3)
        max_participants = int(num_participants.split('-')[1])
        
        if len(human_members) < max_participants:
            logger.warning(f"Channel only has {len(human_members)} human members, using all of them")
            conversation_participants = human_members
        else:
            conversation_participants = random.sample(human_members, max_participants)

        # Get user info for each participant
        participant_info = []
        for participant_id in conversation_participants:
            try:
                user_info = client.users_info(user=participant_id)
                participant_info.append({
                    'id': participant_id,
                    'name': user_info['user']['name'],
                    'real_name': user_info['user'].get('real_name', ''),
                    'display_name': user_info['user']['profile'].get('display_name', ''),
                    'title': user_info['user']['profile'].get('title', ''),
                    'avatar': user_info['user']['profile'].get('image_192', '')
                })
                logger.debug(f"Got info for participant {participant_id}: {participant_info[-1]}")
            except Exception as e:
                logger.error(f"Error getting info for participant {participant_id}: {e}")
                continue
        logger.debug(f"Selected {len(conversation_participants)} participants from {len(human_members)} human members")
        # Generate conversation posts


        # Create a dictionary with all conversation parameters
        conversation_params = {
            "company_name": company_name,
            "industry": industry,
            "topics": topics,
            "custom_prompt": custom_prompt,
            "num_participants": num_participants,
            "num_posts": num_posts,
            "post_length": post_length,
            "tone": tone,
            "emoji_density": emoji_density,
            "thread_replies": thread_replies,
            "conversation_participants": conversation_participants,
            "selected_channel": selected_channel,
            "channel_topic": channel_topic,
            "channel_purpose": channel_purpose,
            "is_private": is_private,
            "member_count": member_count,
            "created_ts": created_ts
        }

        # Extract min and max from range (e.g., "5-10" becomes min=5, max=10)
        min_posts, max_posts = map(int, num_posts.split('-'))
        total_posts = random.randint(min_posts, max_posts)
        
        generated_posts = []

        history = {
            "user_id": current_user["id"],
            "channel_id": selected_channel,
            "id": history_row["id"]
        }
        for i in range(total_posts):
            logger.debug(f"Generating post {i+1} of {total_posts}")
            post = factory._fetch_conversation(conversation_params)
            
            for post_item in post:
                post_item["history"] = history.copy() # TODO: this is throwing a problem. Fix it!
                generated_posts.append(post_item)

            view_body = _get_conversation_progress_view(data=conversation_params, total=total_posts, current=i+1)

            # Show loading state
            view_info = client.views_update(
                view_id=original_view_info["view"]["id"],
                view=view_body
            )

        # Post each generated post and its replies to the channel
        post_result_data = logistics._send_conversation(
            client=client, 
            selected_channel=selected_channel,
            post=generated_posts,
            participant_info=participant_info
        )
        post_results = post_result_data["post_results"]
        reply_results = post_result_data["reply_results"]

        # update the history for query time
        query_time = worker.get_time() - start_time
        logger.info(f"Start time = {start_time}; query time: {query_time}")
        db.update("history", {"query_time": query_time}, {"id": history_row["id"]})

        # log an entry to the analytics table
        total_posts_sent = db.fetch_one("SELECT COUNT(*) AS total_posts_sent FROM messages WHERE history_id = %s", (history_row["id"],))["total_posts_sent"]
        db.insert("analytics", {"user_id": current_user["id"], "messages": total_posts_sent})
        
        # TODO: Save conversation definition if selected

        # Update modal to show success
        client.views_update(
            view_id=original_view_info["view"]["id"],
            view={
                "type": "modal",
                "title": {
                    "type": "plain_text",
                    "text": "Conversation Generated"
                },
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "✅ Conversation generated successfully!",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Generated conversation in <#{selected_channel}> with:"
                        }
                    },
                    {
                        "type": "section", 
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Posts:* {len(post_results)}"},
                            {"type": "mrkdwn", "text": f"*Total Replies:* {len(reply_results)}"},
                            {"type": "mrkdwn", "text": f"*Participants:* {num_participants}"},
                            {"type": "mrkdwn", "text": f"*Topics:* {', '.join(topics) if topics else 'Not specified'}"}
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "👉 *View the conversation in the channel to see the results!*"
                        }
                    }
                ]
            }
        )

    except Exception as e:
        logger.error(f"Error in conversation generator submission: {e}")
        logger.error(f"View: {view}")

        # delete the history item
        db.delete("history", {"id": history_row["id"]})
        
        # Check if original_view_info exists before trying to update
        if original_view_info:
            # Update modal to show error
            client.views_update(
                view_id=original_view_info["view"]["id"],
                view={
                    "type": "modal",
                    "title": {
                        "type": "plain_text",
                        "text": "Error"
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"❌ Error generating conversation: {str(e)}"
                            }
                        }
                    ]
                }
            )
        else:
            # If original_view_info doesn't exist, open a new error modal
            client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "title": {
                        "type": "plain_text",
                        "text": "Error"
                    },
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"❌ Error generating conversation: {str(e)}"
                            }
                        }
                    ]
                }
            )
        raise

def _get_conversation_progress_view(data, total, current=0):
    progress = round(current/total * 100)
    view = {
            "type": "modal",
            "title": {
                "type": "plain_text",
                "text": "Generating Conversation"
            },
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"🔄 Generating conversation... {progress}% complete",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Please wait while we generate your conversation with the following parameters:"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Company:* {data['company_name'] or 'Not specified'}"},
                        {"type": "mrkdwn", "text": f"*Industry:* {data['industry']}"},
                        {"type": "mrkdwn", "text": f"*Topics:* {', '.join(data['topics']) if data['topics'] else 'Not specified'}"},
                        {"type": "mrkdwn", "text": f"*Participants:* {data['num_participants']}"},
                        {"type": "mrkdwn", "text": f"*Posts:* {data['num_posts']}"},
                        {"type": "mrkdwn", "text": f"*Length:* {data['post_length']}"},
                        {"type": "mrkdwn", "text": f"*Tone:* {data['tone']}"},
                        {"type": "mrkdwn", "text": f"*Emoji Density:* {data['emoji_density']}"},
                        {"type": "mrkdwn", "text": f"*Thread Replies:* {data['thread_replies']}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Custom Instructions:*\n{data['custom_prompt'] or 'None provided'}"
                    }
                }
            ]
        }
    # logger.debug(f"View: {view}")
    return view

@app.function("converse_thread_extend")
def handle_step_extend_thread(ack: Ack, client, inputs: dict, fail: Fail, complete: Complete, logger: logging.Logger):
    ack()
    
    logger.debug(f"INPUTS: {inputs}")

    try:
        conversation.extend_thread(client, member_id=inputs["member_id"], channel_id=inputs["message_ts"]["channel_id"], message_ts=inputs["message_ts"]["message_ts"])
        complete()
    except Exception as e:
        logger.error(f"Error extending thread via workflow: {e}")
        fail(f"Error extending thread via workflow: {e}")





# NOTE: This is a test definition that is a remote workflow step. The step is defined in the App Manager > Workflow Steps, and it's awesome!
@app.function("hello_world")
def handle_hello_world_event(ack: Ack, inputs: dict, fail: Fail, complete: Complete, logger: logging.Logger):
    ack()
    user_id = inputs["user_id"]
    try:
        output = f"Hello World!"
        complete({"hello_message": output})
    except Exception as e:
        logger.exception(e)
        fail(f"Failed to complete the step: {e}")

# TODO: build a handler for the message shortcut to add conversation to a thread 
@app.shortcut({"callback_id": "thread_generate", "type": "message_action"})
def handle_thread_generate_shortcut(ack, shortcut, client):
    ack()

    # current_user = worker.get_user(client, shortcut["user"]["id"])

    if "thread_ts" in shortcut:
        # if it's a reply, get the parent message ts
        main_ts = shortcut["thread_ts"]
    else:
        main_ts = shortcut["message_ts"]

    conversation.extend_thread(client, shortcut["user"]["id"], shortcut["channel"]["id"], main_ts)


@app.event("app_mention")
def handle_mention_action(event, client):
    logger.debug("EVENT APP MENTIONED!")
    logger.debug(event)

    member_id = event["user"]
    channel_id = event["channel"]
    message_ts = event["ts"]

    conversation.extend_thread(client, member_id=member_id, channel_id=channel_id, message_ts=message_ts)  


# TODO: build a handler to add content to a channel. First show a modal if the context of the current channel cannot be determined
# TODO: This could (maybe???) also be run at the thread level and execute the same function as the message action flow... if the thread ts is known
@app.shortcut({"callback_id": "channel_generate", "type": "shortcut"})
def handle_channel_generate_shortcut(ack, shortcut, client):
    ack()
    logger.info(shortcut)

def main():
    try:
        handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        logger.info("⚡️ Bolt app is running!")
        handler.start()
    except Exception as e:
        logger.error(f"Error starting the app: {e}")
        raise

if __name__ == "__main__":
    main() 