from slack_bolt import App
from slack.errors import SlackApiError
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
from dotenv import load_dotenv
import requests
import json
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
        view = {
            "type": "home",
            "blocks": [
                {
                    "type": "actions",
                    "block_id": "home_buttons",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Create Channels",
                                "emoji": True
                            },
                            "action_id": "open_channel_creator"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Saved Conversations",
                                "emoji": True
                            },
                            "action_id": "view_saved_conversations"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Conversation History",
                                "emoji": True
                            },
                            "action_id": "view_conversation_history"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Conversation Analytics",
                                "emoji": True
                            },
                            "action_id": "view_conversation_analytics"
                        }
                    ]
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "block_id": "channel_select",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Choose a channel to work with:"
                    },
                    "accessory": {
                        "type": "conversations_select",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a channel",
                            "emoji": True
                        },
                        "action_id": "selected_channel",
                        "filter": {
                            "include": ["public", "private"],
                            "exclude_bot_users": True
                        }
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Existing Channels with :white_check_mark: and without :x: Canvas",
                        "emoji": True
                    }
                }
            ]
        }
        
        # Get list of all channels (both public and private)
        channels_list = []
        cursor = None
        
        while True:
            result = client.conversations_list(
                types="public_channel,private_channel",
                cursor=cursor,
                exclude_archived=True
            )
            channels_list.extend(result["channels"])
            cursor = result.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        # Sort channels_list by name
        channels_list.sort(key=lambda x: x["created"], reverse=True)
        
        # Add each channel to the view
        for channel in channels_list:
            channel_id = channel["id"]
            channel_name = channel["name"]
            is_private = channel["is_private"]
            
            # Check if channel has a canvas (you'll need to implement this check based on your storage mechanism)
            has_canvas = False  # Placeholder - implement your check here
            try:
                # Safely check for properties and canvas, defaulting to False if not found
                has_canvas = channel.get("properties", {}).get("canvas", False)
            except Exception as e:
                logger.debug(f"Error checking canvas property for channel {channel_name}: {e}")
                has_canvas = False
            
            
            channel_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ("✅" if has_canvas else "❌") + 
                            f" *<#{channel_id}>*"
                }
            }
            
            # Add generate button if no canvas exists
            # if not has_canvas:
            channel_block["accessory"] = {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Generate Canvas",
                    "emoji": True
                },
                "action_id": "generate_canvas",
                "value": channel_id
            }
            
            view["blocks"].append(channel_block)

        # Publish the view
        client.views_publish(
            user_id=event["user"],
            view=view
        )

    except Exception as e:
        logger.error(f"Error updating home tab: {e}")

@app.action("open_channel_creator")
def handle_open_channel_creator(ack, body, client):
    ack()
    try:
        # Get user ID and any stored values
        user_id = body["user"]["id"]
        stored_values = user_inputs.get(user_id, {})
        
        # Open modal with form
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "channel_creator_submission",
                "title": {
                    "type": "plain_text",
                    "text": "Channel Creator"
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Generate Channels"
                },
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "customer_name_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "customer_name",
                            "initial_value": stored_values.get("customer_name", ""),
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Enter customer name..."
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Customer Name"
                        },
                        "optional": True
                    },
                    {
                        "type": "input",
                        "block_id": "use_case_input",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "use_case",
                            "initial_value": stored_values.get("use_case", ""),
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Describe your use case for channel creation..."
                            },
                            "multiline": True
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Use Case Description"
                        }
                    }
                ]
            }
        )
    except Exception as e:
        logger.error(f"Error opening channel creator modal: {e}")

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
        
    except Exception as e:
        logger.error(f"Error in channel creator submission: {e}")
        client.chat_postMessage(
            channel=user_id,
            text=f"❌ Error creating channels: {str(e)}"
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
            import random
            sample_size = min(5, len(member_ids))
            random_members = random.sample(member_ids, sample_size)
            
            logger.debug(f"Selected random members: {random_members}")

            # Format member IDs with <@ > syntax
            formatted_members = [f"![](@{member_id})" for member_id in random_members]
            logger.debug(f"Formatted member list: {formatted_members}")
            # Join the formatted member list with commas
            member_string = ", ".join(formatted_members)
            logger.debug(f"Member string: {member_string}")

            url = "https://devxp-ai-api.tinyspeck.com/v1/chat/"

            payload = json.dumps({
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a Slack Connect experience architect."
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Create a canvas for the {channel_name} channel.\n"
                            f"The channel description is: {channel_purpose}\n"
                            f"The current topic is: {channel_topic}\n"
                            f"The following users are members of this channel: {member_string} - use exacly this formate to mention them in the canvas content. "
                            "and may be used in the canvas content as key contacts. "
                            "RULE: do not nest bullet points. "
                            "RULE: use rich markdown format. "
                            "RULE: make sure the title of the canvas is the first line in the body. "
                            "RULE: for bullet points use an *"
                        )
                    }
                ],
                "source": "postman",
                "max_tokens": 4096,
                "tools": [{
                    "name": "create_canvas",
                    "description": "Creates Slack canvas content and attaches to a Slack channel.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "canvas": {
                                "type": "object",
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "description": "The heading for the canvas. Keep it relatively short."
                                    },
                                    "body": {
                                        "type": "string",
                                        "description": "Rich content using Slack simple markdown format and emoji."
                                    }
                                },
                                "required": ["title", "body"]
                            }
                        },
                        "description": "A canvas using rich Slack markdown format.",
                        "required": ["canvas"]
                    }
                }],
                "tool_choice": {
                    "type": "tool",
                    "name": "create_canvas"
                }
            })
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + os.environ["DEVXP_API_KEY"]
                }

            response = requests.request("POST", url, headers=headers, data=payload)

            content = response.json()["content"][0]["content"][0]["input"]["canvas"]

            logger.info(content)

            if do_canvas_update:
                canvas_result = client.canvases_edit(
                    canvas_id=channel_details.get("properties", {}).get("canvas", {}).get("file_id"),
                    changes=[{"operation": "replace", "document_content": {"type": "markdown", "markdown": content["body"]}}]
                )
                canvas_id = channel_details.get("properties", {}).get("canvas", {}).get("file_id")
            else:
                canvas_result = client.conversations_canvases_create(
                    channel_id=selected_channel,
                    document_content={"type": "markdown", "markdown": content["body"]}
                )
                canvas_id = canvas_result["canvas_id"]
            
            # Get canvas file info
            canvas_info = client.files_info(file=canvas_id)
            logger.info(f"Canvas file info: {canvas_info['file']}")
            
            # Extract permalink
            canvas_permalink = canvas_info["file"]["permalink"]
            logger.info(f"Canvas permalink: {canvas_permalink}")
            # Send DM to user about canvas creation/update
            client.chat_postMessage(
                channel=body["user"]["id"],
                text=f"{'Updated' if do_canvas_update else 'Created'} canvas for <#{selected_channel}>\n" +
                     f"View it here: <{canvas_permalink}|{content['title']}>"
            )

            logger.info(canvas_result)

            # After successful canvas generation, refresh the channel details modal
            channel_info = client.conversations_info(channel=selected_channel, include_num_members=True)
            channel = channel_info["channel"]
            history = client.conversations_history(channel=selected_channel, limit=1)
            
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

@app.action("selected_channel")
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
            members = client.conversations_members(channel=selected_channel)["members"]
            
            # If bot is not a member
            if bot_user_id not in members:
                # Check if channel is private
                channel_info = client.conversations_info(channel=selected_channel)
                if channel_info["channel"]["is_private"]:
                    # Show error modal for private channel
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
                else:
                    # Join public channel
                    client.conversations_join(channel=selected_channel)
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