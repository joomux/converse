import os
import requests
import json
import random
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def thread(description: str, topic: str, thread: dict, members: list):
    url = os.environ.get("AI_API")

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
                                    "description": "The name of the authore posting the reply message. This is alphanumeric only."
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


def _build_mention_string(user_list):
    return ", ".join([f"<@{user_id}>" for user_id in random.sample(user_list, len(user_list))])