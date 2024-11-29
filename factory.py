import os
import requests
import random

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

    # TODO: handle errors better here and make sure the structure has the 'conversations' object
    
    return response.json()["content"][0]["content"][0]["input"]["conversations"]