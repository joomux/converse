from logging import Logger
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import Ack, Say
from ai import devxp
from utils.database import Database, DatabaseConfig
from utils import builder
from utils.conversation_model import Conversation
from utils.app_view import render_app_view
import json, os

db = Database(DatabaseConfig())

def create_channels(ack: Ack, body, client: WebClient, view, logger: Logger, say: Say):
    ack()
    # Move the channel generation logic from handle_generate_channels here
    user_id = body["user"]["id"]
    # Fetch team ID
    app_installed_team_id = body["view"]["app_installed_team_id"]
    try:
        state_values = view["state"]["values"]

        user_inputs = {}
        
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
        # view_modal = client.views_open(
        #     trigger_id=body["trigger_id"],
        #     view={
        #         "type": "modal",
        #         "title": {
        #             "type": "plain_text",
        #             "text": "Figuring out channels..."
        #         },
        #         "blocks": [
        #             {
        #                 "type": "section",
        #                 "text": {
        #                     "type": "mrkdwn",
        #                     "text": "🔄 Generating channels based on your input...\nThis may take a few moments."
        #                 }
        #             }
        #         ]
        #     }
        # )

        view_path = os.path.join("block_kit", "loading.json")
        with open(view_path, 'r') as file:
            loading_modal = json.load(file)
        view_modal =client.views_open(trigger_id=body["trigger_id"], view=loading_modal)

        try:

            channels_list = devxp.fetch_channels(customer_name, use_case)
            # created_channels = logistics._send_channels(client, user_id, channels_list)
            created_channels = []
            blocks = []
            for channel_def in channels_list:
                logger.info(channel_def)
                try:
                    # channel_created = client.conversations_create(
                    #     name=channel_def["name"],
                    #     is_private=channel_def["is_private"]==1
                    # )
                    # # Set channel topic and purpose if provided
                    # if "topic" in channel_def:
                    #     client.conversations_setTopic(
                    #         channel=channel_created["channel"]["id"],
                    #         topic=channel_def["topic"]
                    #     )
                    
                    # if "description" in channel_def:
                    #     client.conversations_setPurpose(
                    #         channel=channel_created["channel"]["id"], 
                    #         purpose=channel_def["description"]
                    #     )
                    
                    # # Add user as member and channel owner
                    # client.conversations_invite(
                    #     channel=channel_created["channel"]["id"],
                    #     users=user_id
                    # )

                    conversation = Conversation(
                        channel_name=channel_def["name"],
                        channel_topic=channel_def["topic"],
                        channel_description=channel_def["description"],
                        channel_is_private=channel_def["is_private"]
                    ).format()
                    created_channels.append(conversation)

                    blocks.append(
                        {
                            "type": "rich_text_section",
                            "elements": [
                                {
                                    "type": "text",
                                    "text": f"#{channel_def['name']}{' (private)' if channel_def['is_private'] else ''}"
                                }
                            ]
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Error creating channel {channel_def['name']}: {e}")
                    continue
            
            result = builder.get_user_selections(user_id=user_id, app_installed_team_id=app_installed_team_id, logger=logger)
            logger.debug(created_channels)

            # Fix: Store both the channels and use case in a dictionary
            result["channels"]["create"] = {
                "channels": created_channels,
                "use_case": use_case
            }

            # now update the database row
            builder.save_user_selections(
                user_id=user_id,
                app_installed_team_id=app_installed_team_id,
                selections=result,
                logger=logger
            )
            

            # TODO: Could store this in some temporary place to reference on the builder main view
            # Close loading modal
            client.views_update(
                view_id=view_modal["view"]["id"],
                view={
                    "type": "modal", 
                    "title": {
                        "type": "plain_text", 
                        "text": "Creating Channels"
                    }, 
                    "close": {
                        "type": "plain_text", 
                        "text": "OK"
                    },
                    "callback_id": "modal_channel_creater_result",
                    "notify_on_close": True,
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"{len(created_channels)} channels to be created. Note that these channels have not been created yet. They will be created when the demo content is generated.\n" 
                            }
                        },
                        {
                            "type": "rich_text",
                            "elements": [
                                {
                                    "type": "rich_text_list",
                                    "style": "bullet",
                                    "indent": 0,
                                    "elements": blocks
                                }
                            ]
                        }
                    ]
                    }
            )
            # render_app_view(
            #     client=client,
            #     user_id=user_id,
            #     app_installed_team_id=app_installed_team_id,
            #     view_type="builder_step_1",
            #     logger=logger
            # )
        except Exception as e:
            logger.error(f"Error in channel creation: {e}")

    except Exception as e:
        logger.error(f"Error in channel creator submission: {e}")
        # client.chat_postMessage(
        #     channel=user_id,
        #     text=f"❌ Error creating channels: {str(e)}"
        # )
        # say(
        #     channel=user_id,
        #     text=f"❌ Error creating channels: {str(e)}"
        # )
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

def select_channels(ack: Ack, body, client: WebClient, view, logger: Logger, say: Say):
    ack()
    logger.info("VIEWS > SELECT CHANNELS")
    user_id = body["user"]["id"]
    try:
        state_values = view["state"]["values"]

        user_inputs = {}

        # logger.info("SELECT CHANNELS - BODY....")
        # logger.info(body)

        # logger.info("SELECT CHANNELS - VIEW....")
        # logger.info(view)
        # {'channels_selected': {'channels': {'type': 'multi_conversations_select', 'selected_conversations': ['C082QN4TJ85', 'C07VAASC5A8']}}}
        
        # Fetch team ID
        app_installed_team_id = body["view"]["app_installed_team_id"]

        result = builder.get_user_selections(user_id=user_id, app_installed_team_id=app_installed_team_id, logger=logger)

        # logger.debug("DB RESULT")
        # logger.debug(result)

        if "channels" not in result: # make sure we have a dict to work with
            result["channels"] = {}
        if "selected" not in result["channels"]:
            result["channels"]["selected"] = []
        
        channels = state_values["channels_selected"]["channels"]["selected_conversations"]

        # need to build a conversation object from each of these selected channels!
        selected_conversations = []
        for channel_id in channels:
            conversation = Conversation(channel_id=channel_id).format()
            selected_conversations.append(conversation)
        
        logger.debug(selected_conversations)
        result["channels"]["selected"] = selected_conversations # this is an array/list

        # now update the database row
        builder.save_user_selections(
            user_id=user_id,
            app_installed_team_id=app_installed_team_id,
            selections=result,
            logger=logger
        )

        # TODO: update the home view here??? Or call a render_home_view function to do it all!
        render_app_view(
            client=client,
            user_id=user_id,
            app_installed_team_id=app_installed_team_id,
            view_type="builder_step_1",
            logger=logger
        )
        
    except Exception as e:
        logger.error(f"Error in select_channels: {e}")


def reload_app_home(ack: Ack, body, client: WebClient, view, logger: Logger, say: Say):
    ack()
    logger.info("VIEWS>CHANNEL: RELOAD APP HOME")
    user_id = body["user"]["id"]
    app_installed_team_id = body["view"]["app_installed_team_id"]
    
    render_app_view(
        client=client,
        user_id=user_id,
        app_installed_team_id=app_installed_team_id,
        view_type="builder_step_1",
        logger=logger
    )