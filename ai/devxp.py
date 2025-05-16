import os
import requests
import json
import random
import logging

logging.basicConfig(level=os.environ.get('LOGLEVEL', logging.DEBUG))
logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get("AI_API")

def fetch_message(author: str, conversation_participants: list, purpose: str, channel_topic: str, topic: str, length: str, tone: str, emoji_density: str = "average", custom_prompt: str = ""):
    logger.info("DEVXP.FETCH_MESSAGE")
    logger.info(f"author: {author}")
    logger.info(f"conversation_participants: {conversation_participants}")
    logger.info(f"purpose: {purpose}")
    logger.info(f"channel_topic: {channel_topic}")
    logger.info(f"topic: {topic}")
    logger.info(f"length: {length}")
    logger.info(f"tone: {tone}")
    logger.info(f"emoji_density: {emoji_density}")
    logger.info(f"custom_prompt: {custom_prompt}")


    url = API_BASE_URL

    # author = user id in full format

    content = (
        "I am a Solution Engineer at Slack, creating a demo to showcase Slack's features using realistic conversations. "
        f"Generate a Slack post from the user: {author}. The post may optionally mention any of the following users: {_build_mention_string(conversation_participants)}. "
    )

    if purpose:
        content += f"The purpose of this channel is: {purpose}."

    if channel_topic:
        content += f"The current channel topic is: '{channel_topic}'. "
    
    if topic:
        content += f"The topic of this post is: {topic}. "

    length_opts = {
        "short": random.randrange(1, 2),
        "medium": random.randrange(1, 5),
        "long": random.randrange(1, 10)
    }
    if isinstance(length, str) and not length_opts[length]:
        length = "medium"

    content += (
        f"The length of the post should be {length_opts[length]} sentences, and can optionally use simple markdown (*bold*, _italic_, `inline code`, ```code block```) if appropriate. "
        "RULES: \n"
        f"- TONE: The tone of the post is {tone}. \n"
        "- VOICE: Ensure this author has a unique voice and the post sounds authentic. \n"
        f"- EMOJI: Standard Slack emoji only. Use a {emoji_density} number of emojis in the message content. \n"
        "- REACJI: Limit reactions (0-4 reacjis per message).\n"
        "MENTIONS: User Mentions: Mention only the specified users, with no additional names. \n"
        "FORMAT: Do not format topics or keywords with ** marks.\ n"
    )

    if custom_prompt:
        content += f"\n\n CUSTOM INSTRUCTIONS: {custom_prompt}."
    
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
        "temperature": 1,
        "source":"converse_demo_app",
        "max_tokens":2000,
        "tools":[
            {
                "name":"get_message",
                "description":"Format a Slack post as returned from Claude.",
                "input_schema":{
                "type":"object",
                "properties":{
                    "channel_post":{
                        "type":"array",
                        "items":{
                            "type":"object",
                            "properties":{
                            "author":{
                                "type":"string",
                                "description":"The name of the author posting the message. This is alphanumeric only."
                            },
                            "message":{
                                "type":"string",
                                "description":f"The content of the Slack message posted by the author. Bold text is enclosed in single *, Underlined text is inclosed in _, Code is inclosed in `, blocks of code or highly technical details are inclosed in ```, and text to strike through is enclosed in ~. There should be {length_opts[length]} sentences."
                            },
                            "reacjis":{
                                "type":"array",
                                "items":{
                                    "type":"string"
                                },
                                "description":"A list of emojis used in response to this Slack message."
                            }
                            },
                            "required":[
                            "author",
                            "message"
                            ]
                        },
                        "description":"A structured Slack message."
                    }
                },
                "required":[
                    "channel_post"
                ]
                }
            }
        ],
        "tool_choice":{
            "type":"tool",
            "name":"get_message"
        }
    }


    logger.debug(f"FETCH_MESSAGE prompt: {payload}")

    headers = {
        'Content-Type': 'application/json',
        'Authorization': os.environ.get('DEVXP_API_KEY', '')
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # Raise an exception for bad status codes

    # TODO: handle errors better here and make sure the structure has the 'conversations' object
    
    return response.json()["content"][0]["content"][0]["input"]["channel_post"][0]


def fetch_conversation(conversation_params):
    url = API_BASE_URL

    content = (
        "I am a Solution Engineer at Slack, creating a demo to showcase Slack's features "
        f"using realistic conversations. Generate a Slack conversations among the following users: {_build_mention_string(conversation_params['conversation_participants'])}.\n\n"
    )

    if "company" in conversation_params:
        content += f"Company: {conversation_params['company_name']}\n"
    

    if "industry" in conversation_params:
        content += (
            f"Context: {conversation_params['industry']} industry\n"
        )

    content += (
        #f"Structure: It should have between {conversation_params['thread_replies']} threaded replies. \n"
        f"Structure: It should have {random.randrange(start=_parse_range(conversation_params['thread_replies'])['min'], stop=_parse_range(conversation_params['thread_replies'])['max'])} threaded replies. \n"
    )

    if "channel_topic" in conversation_params:
        content += f"The current channel topic is: '{conversation_params['channel_topic']}'\n"

    if isinstance(conversation_params['topics'], list) and conversation_params['topics']:
        conversation_params['topics'] = ', '.join(conversation_params['topics'])
    content += (    
        # {', '.join(conversation_params['topics'])} \n"
        f"The purpose of the channel where this conversation is occurring is: {conversation_params['channel_purpose']} \n"
        f"The length of the initial post should be {conversation_params['post_length']}, using simple markdown (*bold*, _italic_, `inline code`, ```code block```).\n"
        "Voices: Ensure each user has a distinct perspective and voice. Avoid templated messages; aim for authenticity and variety.\n"
    )
    if conversation_params['topics']:
        content += f"Topics: {conversation_params['topics']}\n"
    
    content += (
        f"Tone: {conversation_params['tone']}\n"
        f"Emoji: Standard Slack emoji only. Use {conversation_params['emoji_density']} emojis in some of the message content. "
        "Limit reactions (0-4 reacjis per message).\n"
        "User Mentions: Mention only the specified users, with no additional names. "
        "Do not format topics or keywords with ** marks."
    )

    if "custom_prompt" in conversation_params:
        content += f"\n{conversation_params['custom_prompt']}\n"

    # logger.debug(f"\n\n{conversation_params}\n\n")
    # logger.debug(f"\n\n{content}\n\n")

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
                                    "description": "The name of the author posting the message. This is alphanumeric only."
                                },
                                "message": {
                                    "type": "string",
                                    "description": "The content of the message posted by the author. "
                                                 "Bold text is enclosed in single *, Underlined text is inclosed in _, "
                                                 "Code is inclosed in `, and text to strike through is enclosed in ~. "
                                                #  "There should be approximately 5 sentences."
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
                                    "description": f"A structured set of {random.randrange(start=_parse_range(conversation_params['thread_replies'])['min'], stop=_parse_range(conversation_params['thread_replies'])['max'])} message sent in reply to the previous message. "
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

    logger.debug(f"FETCH_CONVERSATION prompt: {payload}")

    headers = {
        'Content-Type': 'application/json',
        'Authorization': os.environ.get('DEVXP_API_KEY', '')
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # Raise an exception for bad status codes

    # TODO: handle errors better here and make sure the structure has the 'conversations' object
    
    return response.json()["content"][0]["content"][0]["input"]["conversations"]

def thread(description: str, topic: str, thread: dict, members: list, replies: int = 0):
    logger.info("DEVXP.THREAD")
    logger.info(f"description: {description}")
    logger.info(f"topic: {topic}")
    logger.info(f"thread: {thread}")
    logger.info(f"members: {members}")
    logger.info(f"replies: {replies}")

    url = API_BASE_URL

    if not replies:
        replies = "reasonable number of"

    prompt = (
        "I am a solution engineer at Slack, creating a demo to showcase the value of Slack and using realistic conversations to do so. "
        "You will read the content of an existing thread along with the channel description and current topic. You will then generate a "
        f"{replies} additional replies to extend the conversation."
        f"\nCHANNEL DESCRIPTION: {description}"
        f"\nCHANNEL TOPIC: {topic}"
        "\nEXISTING CONVERSATION:"
        f"\n{thread}" # TRY TO JUST JSON STRIGIFY THIS AND SEE WHAT HAPPENS!
        f"\nLIST OF USERS: {_build_mention_string(members)}"
        "\n\"\"\"\nRULES:"
        "\nEach message should feel authentic and be unique in structure, format and tone."
        "\nEach reply should be between 1 and 5 sentences in length."
        "\nUse applicable standard Slack emoji."
        "\nMention only users from the list of users provided. Do not create additional names."
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
        "temperature": 1,
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
                                    "description": "The reply Slack message. Bold text is enclosed in single *, Underlined text is inclosed in _, Code is inclosed in `, blocks of code or highly technical details are inclosed in ```, and text to strike through is enclosed in ~."
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



def fetch_canvas(channel_name: str = "", channel_purpose: str = "", channel_topic: str = "", member_list: list = [None]):

    # Format member IDs with <@ > syntax
    formatted_members = [f"![](@{member_id})" for member_id in member_list]
    logger.debug(f"Formatted member list: {formatted_members}")
    # Join the formatted member list with commas
    member_string = ", ".join(formatted_members)
    logger.debug(f"Member string: {member_string}")
    
    url = API_BASE_URL

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



def design_channel(channel_name: str, channel_topic: str, channel_description: str):
    url = API_BASE_URL

    prompt = (
        "Design the parameters needed to simulate a Slack channel for a Slack demonstration. Assume the type of personas in the conversation based on the following details. "
        "\nBased on the details of the channel, determine the variables required to design a simulated conversation. "
        f"\nCHANNEL NAME: {channel_name}"
    )
    if channel_topic:
        prompt += (
            f"\nCURRENT TOPIC: {channel_topic}"
        )
    if channel_description:
        prompt += (
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
                        "description": "The range of people to include in the conversation. Values are: 2-3, 5-10, 11-20"
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

def _parse_range(range: str):
    # ints = range.split('-')
    try:
        ints = [int(i) for i in range.split('-')]
    except ValueError as e:
        logger.error(f"Error converting range to integers: {e}")
        raise
    return {"min": min(ints), "max": max(ints)}