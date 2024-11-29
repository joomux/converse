import os
import requests
import random
import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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

    if "custom_prompt" in conversation_params:
        content += f"\n{conversation_params['custom_prompt']}\n"

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

    # TODO: handle errors better here and make sure the structure has the 'conversations' object
    
    return response.json()["content"][0]["content"][0]["input"]["conversations"]


def _fetch_canvas(channel_name="", channel_purpose="", channel_topic="", member_list: list = [None]):

    # Format member IDs with <@ > syntax
    formatted_members = [f"![](@{member_id})" for member_id in member_list]
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

    return content

def _fetch_channels(customer_name: str, use_case: str):
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

    return channels_list