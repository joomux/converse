from slack_bolt import App
from slack.errors import SlackApiError
from slack_bolt.adapter.socket_mode import SocketModeHandler
import os
from dotenv import load_dotenv
import requests
import random
import json
import logging
import time

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
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Let's build a demo!",
                        "emoji": True
                    }
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
                }
            ]
        }

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
                            f"I need to design a series of Slack channels aimed to solve for "
                            f"the following use case(s) for the company called {customer_name}: "
                            f"{use_case}. Provided suggested channel names and descriptions. "
                            "Use a consistent naming pattern and prefix."
                        )
                    }
                ],
                "source": "postman",
                "max_tokens": 2048,
                "tools": [{
                    "name": "create_channels",
                    "description": "Creates a set of Slack channels for a specific use case.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "channels": {
                                "type": "array",
                                "description": "The parameters to define a new channel in Slack",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "The name of the channel in the format supported by Slack channel names"
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "A human-friendly description of the channel"
                                        },
                                        "topic": {
                                            "type": "string",
                                            "description": "What the topic of the channel is currently about. Slack markdown format supported."
                                        },
                                        "is_private": {
                                            "type": "integer",
                                            "description": "Indicates if the channel should be private or public. Use 1 for private or 0 for public."
                                        }
                                    },
                                    "required": ["name", "description", "is_private"]
                                }
                            }
                        },
                        "required": ["channels"]
                    }
                }],
                "tool_choice": {
                    "type": "tool",
                    "name": "create_channels"
                }
            })
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + os.environ["DEVXP_API_KEY"]
            }

            response = requests.request("POST", url, headers=headers, data=payload)

            logger.info(response.json())

            channels_list = response.json()["content"][0]["content"][0]["input"]["channels"]
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
                    dm_result = client.chat_postMessage(
                        channel=user_id,
                        text=f"✨ Created channel <#{channel_created['channel']['id']}>\n" + 
                            (f"> {channel_def.get('description', 'No description provided')}")
                    )

                    created_channels.append(channel_created["channel"]["id"])
                    
                except SlackApiError as e:
                    logger.error(f"Error creating channel {channel_def['name']}: {e}")
                    
            client.chat_postMessage(
                channel=user_id,
                text=f"✅ Created {len(created_channels)} channels:\n" + "\n".join([f"<#{channel_id}>" for channel_id in created_channels])
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
        client.chat_postMessage(
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

@app.action("generate_conversation")
def handle_generate_conversation(ack, body, client, logger):
    ack()
    try:
        selected_channel = body["actions"][0]["value"]
        logger.info(f"Generating conversation for channel: {selected_channel}")

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

            # Get member list for the channel
            members_response = client.conversations_members(channel=selected_channel)
            member_ids = members_response["members"]

        except Exception as e:
            logger.error(f"Error getting channel info: {e}")
            raise

        # Update modal with form
        client.views_update(
            view_id=body["container"]["view_id"],
            view={
                "type": "modal",
                "callback_id": "conversation_generator_modal",
                "title": {
                    "type": "plain_text", 
                    "text": "Generate Conversation"
                },
                "submit": {
                    "type": "plain_text",
                    "text": "Generate"
                },
                "private_metadata": selected_channel,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"Building conversation for #{channel_name}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "company_name",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "company_name_input",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Enter company name"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Company Name (Optional)"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "industry",
                        "element": {
                            "type": "static_select",
                            "action_id": "industry_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select industry"
                            },
                            "options": [
                                {"text": {"type": "plain_text", "text": "Technology"}, "value": "technology"},
                                {"text": {"type": "plain_text", "text": "Healthcare"}, "value": "healthcare"},
                                {"text": {"type": "plain_text", "text": "Finance"}, "value": "finance"},
                                {"text": {"type": "plain_text", "text": "Manufacturing"}, "value": "manufacturing"},
                                {"text": {"type": "plain_text", "text": "Retail"}, "value": "retail"}
                            ]
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Industry"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "topics",
                        "optional": True,
                        "element": {
                            "type": "multi_static_select",
                            "action_id": "topics_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select topics"
                            },
                            "options": [
                                {"text": {"type": "plain_text", "text": "Product Development"}, "value": "product"},
                                {"text": {"type": "plain_text", "text": "Marketing"}, "value": "marketing"},
                                {"text": {"type": "plain_text", "text": "Sales"}, "value": "sales"},
                                {"text": {"type": "plain_text", "text": "Customer Support"}, "value": "support"},
                                {"text": {"type": "plain_text", "text": "Engineering"}, "value": "engineering"}
                            ]
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Choose Topics (Optional)"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "custom_prompt",
                        "optional": True,
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "custom_prompt_input",
                            "multiline": True,
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Enter any specific instructions for conversation generation"
                            }
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Custom Prompt Instructions (Optional)"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "num_participants",
                        "element": {
                            "type": "static_select",
                            "action_id": "participants_select",
                            "options": [
                                {"text": {"type": "plain_text", "text": "2-3"}, "value": "2-3"},
                                {"text": {"type": "plain_text", "text": "4-6"}, "value": "4-6"},
                                {"text": {"type": "plain_text", "text": "7-10"}, "value": "7-10"},
                                {"text": {"type": "plain_text", "text": "11-15"}, "value": "11-15"}
                            ]
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Number of Participants"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "num_posts",
                        "element": {
                            "type": "static_select",
                            "action_id": "posts_select",
                            "options": [
                                {"text": {"type": "plain_text", "text": "5-10"}, "value": "5-10"},
                                {"text": {"type": "plain_text", "text": "11-20"}, "value": "11-20"},
                                {"text": {"type": "plain_text", "text": "21-30"}, "value": "21-30"},
                                {"text": {"type": "plain_text", "text": "31-50"}, "value": "31-50"}
                            ]
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Number of Channel Posts"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "post_length",
                        "element": {
                            "type": "static_select",
                            "action_id": "length_select",
                            "options": [
                                {"text": {"type": "plain_text", "text": "Short (1-2 sentences)"}, "value": "short"},
                                {"text": {"type": "plain_text", "text": "Medium (3-4 sentences)"}, "value": "medium"},
                                {"text": {"type": "plain_text", "text": "Long (5+ sentences)"}, "value": "long"}
                            ]
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Approximate Length of Each Post"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "tone",
                        "element": {
                            "type": "static_select",
                            "action_id": "tone_select",
                            "options": [
                                {"text": {"type": "plain_text", "text": "Formal"}, "value": "formal"},
                                {"text": {"type": "plain_text", "text": "Casual"}, "value": "casual"},
                                {"text": {"type": "plain_text", "text": "Professional"}, "value": "professional"},
                                {"text": {"type": "plain_text", "text": "Technical"}, "value": "technical"},
                                {"text": {"type": "plain_text", "text": "Executive"}, "value": "executive"},
                                {"text": {"type": "plain_text", "text": "Legal"}, "value": "legal"}
                            ]
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Tone of Conversation"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "emoji_density",
                        "element": {
                            "type": "static_select",
                            "action_id": "emoji_select",
                            "options": [
                                {"text": {"type": "plain_text", "text": "Few"}, "value": "few"},
                                {"text": {"type": "plain_text", "text": "Average"}, "value": "average"},
                                {"text": {"type": "plain_text", "text": "A Lot"}, "value": "lot"}
                            ]
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Emoji Density"
                        }
                    },
                    {
                        "type": "input",
                        "block_id": "thread_replies",
                        "element": {
                            "type": "static_select",
                            "action_id": "replies_select",
                            "options": [
                                {"text": {"type": "plain_text", "text": "0-2 replies"}, "value": "0-2"},
                                {"text": {"type": "plain_text", "text": "3-5 replies"}, "value": "3-5"},
                                {"text": {"type": "plain_text", "text": "6-10 replies"}, "value": "6-10"},
                                {"text": {"type": "plain_text", "text": "11+ replies"}, "value": "11+"}
                            ]
                        },
                        "label": {
                            "type": "plain_text",
                            "text": "Approximate Thread Replies"
                        }
                    }
                ]
            }
        )

    except Exception as e:
        logger.error(f"Error generating conversation: {e}")
        client.chat_postEphemeral(
            channel=body["container"]["channel_id"],
            user=body["user"]["id"],
            text=f"❌ Error: Unable to generate conversation.\nDetails: {str(e)}"
        )

@app.view("conversation_generator_modal")
def handle_conversation_generator_submission(ack, body, client, view, logger):
    ack()
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

        # view_body = _get_conversation_progress_view(data=conversation_params, total=total_posts, current=0)

        # # Show loading state
        # original_view_info = client.views_open(
        #     trigger_id=body["trigger_id"],
        #     view=view_body
        # )
        
        generated_posts = []
        for i in range(total_posts):
            logger.debug(f"Generating post {i+1} of {total_posts}")
            post = _fetch_conversation(conversation_params)
            # logger.debug("--------------------------------")
            # logger.debug(f"Generated post: {post}")
            # logger.debug("--------------------------------")
            for post_item in post:
                generated_posts.append(post_item)

            view_body = _get_conversation_progress_view(data=conversation_params, total=total_posts, current=i+1)

            # Show loading state
            view_info = client.views_update(
                view_id=original_view_info["view"]["id"],
                view=view_body
            )
        # Post each generated post and its replies to the channel

        post_results = []
        reply_results = []
        for post in generated_posts:
            try:
                # Find the participant info for the user who's posting
                participant = next(
                    (p for p in participant_info if p['id'] == ''.join(c for c in post["author"] if c.isalnum())),
                    None
                )

                if participant:
                    # Use the actual user ID for posting
                    post["user"] = participant["id"]
                else:
                    logger.warning(f"Could not find participant info for user {post['user']}")
                    raise Exception(f"Could not find participant info for user {post['user']}")
                
                # logger.debug("--------------------------------")
                # logger.debug(f"Participant: {participant}")
                # logger.debug("--------------------------------")
                # Post the main message
                main_post = client.chat_postMessage(
                    channel=selected_channel,
                    text=post["message"],
                    username=participant["real_name"],
                    icon_url=participant["avatar"]
                )

                post_results.append(main_post)

                if "reacjis" in post and post["reacjis"]:
                    for reaction in post["reacjis"]:
                        try:
                            client.reactions_add(
                                channel=selected_channel,
                                timestamp=main_post["ts"],
                                name=reaction
                            )
                        except Exception as e:
                            logger.error(f"Error adding reaction {reaction} to post {main_post['ts']}: {e}")
                            continue

                # If there are threaded replies, post them in the thread
                if "replies" in post and post["replies"]:
                    for reply in post["replies"]:
                        # Find participant info for the reply user
                        reply_participant = next(
                            (p for p in participant_info if p['id'] == ''.join(c for c in reply["author"] if c.isalnum())),
                            None
                        )

                        if reply_participant:
                            reply["user"] = reply_participant["real_name"]
                        else:
                            logger.warning(f"Could not find participant info for reply user {reply['user']}")
                            raise Exception(f"Could not find participant info for reply user {reply['user']}")
                        
                        # logger.debug("--------------------------------")
                        # logger.debug(f"Participant: {reply_participant}")
                        # logger.debug("--------------------------------")

                        reply_post = client.chat_postMessage(
                            channel=selected_channel,
                            thread_ts=main_post["ts"],
                            text=reply["message"],
                            username=reply_participant["real_name"],
                            icon_url=reply_participant["avatar"]
                        )

                        reply_results.append(reply_post)

                        if "reacjis" in reply and reply["reacjis"]:
                            for reaction in reply["reacjis"]:
                                try:
                                    client.reactions_add(
                                        channel=selected_channel,
                                        timestamp=reply_post["ts"],
                                        name=reaction
                                    )
                                except Exception as e:
                                    logger.error(f"Error adding reaction {reaction} to reply post {reply_post['ts']}: {e}")
                                    continue

                # Add slight delay between posts to avoid rate limits
                time.sleep(1)

            except SlackApiError as e:
                logger.error(f"Error posting message to channel: {e}")
                continue
        
        logger.info("Starting conversation generation with parameters:", {
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
        })

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

def _fetch_conversation(conversation_params):
    """
    Fetch a generated conversation from the DevXP API based on provided parameters.
    
    Args:
        conversation_params (dict): Parameters controlling the conversation generation
            including company_name, industry, topics, etc.
    
    Returns:
        dict: Generated conversation data
    """
    url = "https://devxp-ai-api.tinyspeck.com/v1/chat/"
    
    # Build the content string based on parameters
    content = (
        "I am a Solution Engineer at Slack, creating a demo to showcase Slack's features "
        "using realistic conversations. Generate a Slack conversations among the following users: "
        ", ".join([f"<@{user_id}>" for user_id in random.sample(conversation_params["conversation_participants"], len(conversation_params["conversation_participants"]))]) + ".\n\n"
        f"Context: {conversation_params['industry']} industry\n"
        f"Structure: It should have between {conversation_params['thread_replies']} threaded replies. \n"
        f"The current topic is: {conversation_params['topics']} \n"
        f"The purpose of the channel where this conversation is occurring is: {conversation_params['channel_purpose']} \n"
        f"The initial post should be {conversation_params['post_length']}, using simple markdown (*bold*, _italic_, `code`).\n"
        "Voices: Ensure each user has a distinct perspective and voice. Avoid templated messages; aim for authenticity and variety.\n"
        f"Tone: {conversation_params['tone']}\n"
        f"Emoji: Standard Slack emoji only. Use {conversation_params['emoji_density']} emojis in message content. "
        "Limit reactions (0-4 reacjis per message).\n"
        "User Mentions: Mention only the specified users, with no additional names. "
        "Do not format topics or keywords with ** marks."
    )

    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are a conversation builder for Slack that can simulate conversations between humans."
            },
            {
                "role": "user",
                "content": content
            }
        ],
        "source": "converse_demo_app",
        "max_tokens": 2000,
        "tools": [{
            "name": "get_conversation",
            "description": "Format a Slack conversation as returned from Claude.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "conversations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "author": {
                                    "type": "string",
                                    "description": "The name of the author posting the message"
                                },
                                "message": {
                                    "type": "string",
                                    "description": "The content of the message posted by the author. "
                                                 "Bold text is enclosed in single *, Underlined text is inclosed in _, "
                                                 "Code is inclosed in `, and text to strike through is enclosed in ~. "
                                                 "There should be approximately 5 sentences."
                                },
                                "reacjis": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "A list of emojis used in response to this Slack message."
                                },
                                "replies": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "author": {
                                                "type": "string",
                                                "description": "The name of the author posting the reply message."
                                            },
                                            "message": {
                                                "type": "string",
                                                "description": "The reply message"
                                            },
                                            "reacjis": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                                "description": "An optional list of emojis used in response to this Slack message."
                                            }
                                        },
                                        "required": ["author", "message"]
                                    },
                                    "description": "A structured message sent in reply to the previous message. "
                                                 "There should be approximately 5 replies, though this can vary."
                                }
                            },
                            "required": ["author", "message"]
                        },
                        "description": "A structured Slack conversation message."
                    }
                },
                "required": ["conversations"]
            }
        }],
        "tool_choice": {
            "type": "tool",
            "name": "get_conversation"
        }
    }

    headers = {
        'Content-Type': 'application/json',
        'Authorization': os.environ.get('DEVXP_API_KEY', '')
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # Raise an exception for bad status codes
    
    return response.json()["content"][0]["content"][0]["input"]["conversations"]

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