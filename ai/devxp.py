import os
import requests
import json
import random
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get("AI_API")

def thread(description: str, topic: str, thread: dict, members: list):
    url = API_BASE_URL

    prompt = (
        "I am a solution engineer at Slack, creating a demo to showcase the value of Slack and using realistic conversations to do so. "
        "You will read the content of an existing thread along with the channel description and current topic. You will then generate a "
        "reasonable number of additional replies to extend the conversation."
        f"\nCHANNEL DESCRIPTION: {description}"
        f"\nCHANNEL TOPIC: {topic}"
        "\nEXISTING CONVERSATION:"
        f"\n{thread}" # TRY TO JUST JSON STRIGIFY THIS AND SEE WHAT HAPPENS!
        f"\nLIST OF USERS: {_build_mention_string(members)}"
        "\n\"\"\"\nRULES:"
        "\nEach message should feel authentic and be unique in structure, format and tone."
        "\nEach reply should be between 1 and 5 sentences in length."
        "\nUse applicable standard Slack emoji."
        "\nMention only users from the list provided"
        "\nFormat messages in simplified markdown. For example, *bold*, _italic_, `inline code`, ```code block```"
        "\nStrucure links in the format <link_address|title of link>"
        "\"\"\""
    )

    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are a conversation builder for Slack that can simulate conversations between humans."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "source": "converse_demo_app",
        "max_tokens": 2000,
        "tools": [{
            "name": "extend_thread",
            "description": "Extend an existing Slack thread.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "replies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "author": {
                                    "type": "string",
                                    "description": "The name of the author posting the reply message. This is alphanumeric only."
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
                        "description": "A structured message message send in reply to the previous message. Use a random number between 0 and 10 as the number of replies to generate."
                    }
                },
                "required": ["replies"]
            }
        }],
        "tool_choice": {
            "type": "tool",
            "name": "extend_thread"
        }
    }

    logger.info(payload)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': os.environ.get('DEVXP_API_KEY', '')
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # Raise an exception for bad status codes

    # TODO: handle errors better here and make sure the structure has the 'conversations' object
    
    replies = response.json()["content"][0]["content"][0]["input"]["replies"]

    logger.info(replies)

    return replies



def fetch_channels(customer_name: str, use_case: str):
    url = API_BASE_URL

    payload = json.dumps({
        "messages": [
            {
                "role": "system",
                "content": "You are a Slack experience architect."
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


def design_channel(channel_name: str, channel_topic: str, channel_description: str):
    url = API_BASE_URL

    prompt = (
        "I am a solution engineer at Slack. I need to design a Slack channel for a demonstration. "
        "\nBased on the details of the channel, determine the variables required to design a simulated conversation. "
        f"\nCHANNEL NAME: {channel_name}"
        f"\nCURRENT TOPIC: {channel_topic}"
        f"\nCHANNEL DESCRIPTION: {channel_description}"
    )

    payload = {
        "messages": [
            {
                "role": "system",
                "content": "You are a Slack channel designer."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "source": "converse_demo_app",
        "max_tokens": 2000,
        "tools": [{
            "name": "design_channel",
            "description": "Design a Slack channel with inputs for conversation simulation.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "canvas": {
                        "type": "string",
                        "description": "Should this channel have a generated Slack canvas document attached to it: yes/no"
                    },
                    "topics": {
                        "type":"array",
                        "items":{"type": "string"},
                        "description": "A list of topics to be dicussed in the simulated conversation. Minimum 0, maximum 5 values."
                    },
                    "custom_prompt": {
                        "type": "string",
                        "description": "A customised intruction to be sent to the LLM for simulating conversation data"
                    },
                    "num_participants": {
                        "type": "string",
                        "description": "The range of people to include in the conversation. Values are: 2-3, 5-10, 10-20"
                    },
                    "num_posts": {
                        "type": "string",
                        "description": "The range of channel posts to include in the conversation. Values are: 5-10, 11-20, 21-30, 31-50"
                    },
                    "post_length": {
                        "type": "string",
                        "description": "The range of the length of each channel post. Values are: short, medium, long"
                    },
                    "tone": {
                        "type": "string",
                        "description": "The tone of the conversation to be used. Values are: formal, casual, professional, technical, executive, legal"
                    },
                    "emoji_density": {
                        "type": "string",
                        "description": "The approximate density of emoji to be included in each post of the conversation. Values are: few, average, many"
                    },
                    "thread_replies": {
                        "type": "string",
                        "description": "The approximate number replies to add to each post in the channel. Values are: 0-2, 3-5, 6-10, 11-15"
                    },
                },
                "required": ["canvas", "num_participants", "num_posts", "post_length", "tone", "emoji_density", "thread_replies"],
                "optional": ["topics", "custom_prompt"]
            }
        }],
        "tool_choice": {
            "type": "tool",
            "name": "design_channel"
        }
    }


    logger.info(payload)

    headers = {
        'Content-Type': 'application/json',
        'Authorization': os.environ.get('DEVXP_API_KEY', '')
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # Raise an exception for bad status codes

    # TODO: handle errors better here and make sure the structure has the 'conversations' object
    
    parameters = response.json()["content"][0]["content"][0]["input"]

    logger.info(parameters)

    return parameters


def _build_mention_string(user_list):
    return ", ".join([f"<@{user_id}>" for user_id in random.sample(user_list, len(user_list))])