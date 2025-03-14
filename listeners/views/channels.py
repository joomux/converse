from logging import Logger
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt import Ack, Say
from ai import devxp
from utils.database import Database, DatabaseConfig
from utils import builder

db = Database(DatabaseConfig())

def create_channels(ack: Ack, body, client: WebClient, view, logger: Logger, say: Say):
    ack()
    # Move the channel generation logic from handle_generate_channels here
    user_id = body["user"]["id"]
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

            channels_list = devxp.fetch_channels(customer_name, use_case)
            # created_channels = logistics._send_channels(client, user_id, channels_list)
            created_channels = []
            for channel_def in channels_list:
                logger.info(channel_def)
                try:
                    channel_created = client.conversations_create(
                        name=channel_def["name"],
                        is_private=channel_def["is_private"]==1
                    )
                    # Set channel topic and purpose if provided
                    if "topic" in channel_def:
                        client.conversations_setTopic(
                            channel=channel_created["channel"]["id"],
                            topic=channel_def["topic"]
                        )
                    
                    if "description" in channel_def:
                        client.conversations_setPurpose(
                            channel=channel_created["channel"]["id"], 
                            purpose=channel_def["description"]
                        )
                    
                    # Add user as member and channel owner
                    client.conversations_invite(
                        channel=channel_created["channel"]["id"],
                        users=user_id
                    )

                    # # Add the bot to the channel
                    # client.conversations_invite(
                    #     channel=channel_created["channel"]["id"],
                    #     users=client.auth_test()["user_id"]
                    # )

                    # Send DM to user about channel creation
                    # dm_result = client.chat_postMessage(
                    #     channel=user_id,
                    #     text=f"✨ Created channel <#{channel_created['channel']['id']}>\n" + 
                    #         (f"> {channel_def.get('description', 'No description provided')}")
                    # )

                    created_channels.append(channel_created["channel"]["id"])
                    
                except SlackApiError as e:
                    logger.error(f"Error creating channel {channel_def['name']}: {e}")
                    continue
                    
            # client.chat_postMessage(
            #     channel=user_id,
            #     text=f"✅ Created {len(created_channels)} channels:\n" + "\n".join([f"<#{channel_id}>" for channel_id in created_channels])
            # )
            say(
                channel=user_id,
                text=f"✅ Created {len(created_channels)} channels:\n" + "\n".join([f"<#{channel_id}>" for channel_id in created_channels])
            )

            # TODO: Could store this in some temporary place to reference on the builder main view
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
        say(
            channel=user_id,
            text=f"❌ Error creating channels: {str(e)}"
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
        
        
        result["channels"]["selected"] = list(set(result["channels"]["selected"] + state_values["channels_selected"]["channels"]["selected_conversations"])) # this is an array/list

        # now update the database row
        builder.save_user_selections(
            user_id=user_id,
            app_installed_team_id=app_installed_team_id,
            selections=result,
            logger=logger
        )

        # TODO: update the home view here??? Or call a render_home_view function to do it all!
        
    except Exception as e:
        logger.error(f"Error in select_channels: {e}")