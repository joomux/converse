import os
from logging import Logger
from slack_bolt import Ack, Say
from slack_sdk import WebClient
import json
from utils.conversation_model import Conversation
from ai import devxp
import random
from utils import message, worker, channel, helper
from utils.database import Database, DatabaseConfig
from datetime import timedelta
from functools import lru_cache

# Cache for modal templates to avoid repeated file reads
@lru_cache(maxsize=32)
def load_modal_template(template_name: str) -> dict:
    """Load and cache modal templates from JSON files."""
    view_path = os.path.join("block_kit", f"{template_name}.json")
    with open(view_path, 'r') as file:
        return json.load(file)

def get_channel_info_with_bot_status(client: WebClient, channel_id: str, logger: Logger) -> tuple[dict, bool]:
    """
    Get channel info and bot membership status in a single optimized call.
    Returns tuple of (channel_info, is_bot_member)
    """
    try:
        # Get channel info and members in parallel
        channel_info = client.conversations_info(channel=channel_id, include_num_members=True)
        
        if not channel_info["ok"]:
            logger.error(f"Failed to get channel info for {channel_id}")
            return None, False
            
        members_response = client.conversations_members(channel=channel_id)
        
        # Get bot's user ID (this could be cached at app startup)
        bot_info = client.auth_test()
        bot_user_id = bot_info["user_id"]
        
        # Check if bot is a member
        is_bot_member = bot_user_id in members_response["members"]
        
        return channel_info["channel"], is_bot_member
    
    except Exception as e:
        logger.error(f"Error in get_channel_info_with_bot_status: {e}", exc_info=True)
        return None, False

def single_channel_form(ack: Ack, body, client: WebClient, view, logger: Logger, say: Say):
    try:
        
        logger.info("SINGLE_CHANNEL_FORM RECEIVED PAYLOAD:")
        logger.info(json.dumps(body))
        
        # Load modal template from cache
        conversation_modal = load_modal_template("conversation_modal")
        view_id = body["view"]["id"]
        logger.info(f"Using view_id: {view_id}")
        
        channel_id = body["view"]["state"]["values"]["add_conversation_channel_selector"]["conversation_select"]["selected_conversation"]
        logger.info(f"Selected channel_id: {channel_id}")
        
        # Get channel info and bot status in a single optimized call
        channel_info, is_bot_member = get_channel_info_with_bot_status(client, channel_id, logger)
        
        if not channel_info:
            bot = client.auth_test()
            error_modal = load_modal_template("error_modal")
            error_data = {
                "title": "An error has occurred",
                "error": f"Unable to get information for channel <#{channel_id}>. If this is a private channel, please manually add <@{bot['user_id']}> then try again."
            }
            rendered = helper.render_block_kit(template=error_modal, data=error_data)
            return ack(response_action="update", view=rendered)
        
        # Handle bot membership
        if not is_bot_member:
            if not channel_info["is_private"]:
                try:
                    client.conversations_join(channel=channel_id)
                except Exception as e:
                    logger.error(f"Error adding bot to channel: {e}")
                    bot = client.auth_test()
                    error = f"Unable to add <@{bot['user_id']}> to <#{channel_id}>. Please try again."
                    error_modal = load_modal_template("error_modal")
                    error_data = {
                        "title": "An error has occurred",
                        "error": error
                    }
                    rendered = helper.render_block_kit(template=error_modal, data=error_data)
                    return ack(response_action="update", view=rendered)
            else:
                error = f"Unable to add <@{bot['user_id']}> to <#{channel_id}>. If this is a private channel, please manually add <@{bot['user_id']}> then try again."
                error_modal = load_modal_template("error_modal")
                error_data = {
                    "title": "An error has occurred",
                    "error": error
                }
                rendered = helper.render_block_kit(template=error_modal, data=error_data)
                return ack(response_action="update", view=rendered)

        conversation_modal["private_metadata"] = channel_id

        # Update blocks with proper validation for empty values
        for block in conversation_modal["blocks"]:
            if block.get("block_id") == "channel_topic":
                topic_value = channel_info["topic"]["value"] if channel_info["topic"]["value"] else ""
                if topic_value:
                    block["element"]["initial_value"] = topic_value
                    if len(topic_value) > 150:
                        topic_value = topic_value[:147] + "..."
                    block["element"]["placeholder"] = {"type": "plain_text", "text": topic_value, "emoji": True}
                    logger.info(f"Set topic value: {topic_value}")
                
            if block.get("block_id") == "channel_description":
                purpose_value = channel_info["purpose"]["value"] if channel_info["purpose"]["value"] else ""
                if purpose_value:
                    block["element"]["initial_value"] = purpose_value
                    if len(purpose_value) > 150:
                        purpose_value = purpose_value[:147] + "..."
                    block["element"]["placeholder"] = {"type": "plain_text", "text": purpose_value, "emoji": True}
                    logger.info(f"Set purpose value: {purpose_value}")

        # Use ack() with response_action
        ack(response_action="update", view=conversation_modal)
        # client.views_update(view_id=view_id, view=conversation_modal)
        return

    except Exception as e:
        logger.error(f"Error in single_channel_form: {e}", exc_info=True)
        # Still need to acknowledge even if there's an error
        return False
    
def conversation_generate(ack: Ack, body, client: WebClient, view, logger: Logger, say: Say):
    logger.info("TIME TO GENERATE THE CONVERSATION!")
    
    # First validate all required fields are present
    try:
        state_values = view["state"]["values"]
        
        # Required fields to check
        required_fields = [
            {"block": "channel_topic", "action": "channel_topic_input"},
            # {"block": "channel_description", "action": "channel_description_input"},
            {"block": "num_participants", "action": "do_nothing"},
            {"block": "num_posts", "action": "do_nothing"},
            {"block": "post_length", "action": "do_nothing"},
            {"block": "tone", "action": "do_nothing"},
            {"block": "emoji_density", "action": "do_nothing"},
            {"block": "thread_replies", "action": "do_nothing"}
        ]
        
        errors = {}
        
        for field in required_fields:
            block_id = field["block"]
            action_id = field["action"]
            
            if block_id not in state_values:
                errors[block_id] = f"This field is required"
                continue
                
            if action_id not in state_values[block_id]:
                errors[block_id] = f"This field is required"
                continue
                
            if action_id == "do_nothing":
                # Static select fields
                if "selected_option" not in state_values[block_id][action_id] or not state_values[block_id][action_id]["selected_option"]:
                    errors[block_id] = "Please select an option"
            else:
                # Text input fields
                if "value" not in state_values[block_id][action_id] or not state_values[block_id][action_id]["value"]:
                    errors[block_id] = "This field cannot be empty"
        
        if errors:
            # Return errors to the user
            logger.error(f"Validation errors: {errors}")
            return ack(response_action="errors", errors=errors)
    
    except Exception as e:
        logger.error(f"Error validating conversation form: {e}", exc_info=True)
    
    # If validation passes, acknowledge and proceed with loading modal
    # open the loading model
    view_id = body["view"]["id"]
    view_path = os.path.join("block_kit", "loading.json")
    with open(view_path, 'r') as file:
        loading_modal = json.load(file)
    loading = ack(response_action="update", view=loading_modal) # TODO: use this variable later to update this modal
    logger.info("LOADING VIEW")
    logger.info(loading)

    db = Database(DatabaseConfig()) # so that we can log history events
    current_user = worker.get_user(client, body["user"]["id"])
    channel_id = body["view"]["private_metadata"]

    # Prep the message history log
    history_entry = {
        "conversation_id": None,
        "channel_id": channel_id,
        "user_id": current_user["id"]
    }
    history_row = db.insert("history", history_entry)
    start_time = worker.get_time()
    
    # 0. map all submitted values
    state_values = view["state"]["values"] # submitted value store
    channel_purpose = state_values["channel_description"]["channel_description_input"]["value"]
    channel_topic = state_values["channel_topic"]["channel_topic_input"]["value"]
    topics = state_values["topics"]["topics_select"]["value"]
    custom_prompt = state_values["custom_prompt"]["custom_prompt_input"].get("value", "")
    num_participants = state_values["num_participants"]["do_nothing"]["selected_option"]["value"]
    num_posts = state_values["num_posts"]["do_nothing"]["selected_option"]["value"]
    post_length = state_values["post_length"]["do_nothing"]["selected_option"]["value"]
    tone = state_values["tone"]["do_nothing"]["selected_option"]["value"]
    emoji_density = state_values["emoji_density"]["do_nothing"]["selected_option"]["value"]
    thread_replies = state_values["thread_replies"]["do_nothing"]["selected_option"]["value"]
    try:
        canvas = state_values["canvas"]["do_nothing"]["selected_option"].get('value', False)
        canvas = canvas.lower() == "yes" if canvas is not None else False # this is now a bool
    except Exception as e:
        canvas = False

    # 1. make sure the app is part of this channel and handle if it's a private channel without membership
    channel_info = channel.get_info(
        client=client,
        channel_id=channel_id
    )
    if not channel.is_bot_in_channel(
        client=client,
        channel_id=channel_id
    ): 
        if channel_info["ok"] and not channel_info["is_private"]:
            channel.add_bot_to_channel(
                client=client,
                channel_id=channel_id
            )
        else:
            # unable to add bot to channel!
            bot = client.auth_test()
            error = f"Unable to add <@{bot['user_id']}> to <#{channel_id}>. If this is a private channel, please manually add <@{bot['bot_id']}> then try again."
            # client.chat_postEphemeral(channel=channel_id, user=body["user"]["id"], text=error)
            view_path = os.path.join("block_kit", "error_modal.json")
            with open(view_path, 'r') as file:
                error_modal = json.load(file)
            error_data = {
                "title": "An error has occurred",
                "error": error
            }
            rendered = helper.render_block_kit(template=error_modal, data=error_data)
            return ack(response_action="update", view=rendered)
    
    # ---------------------------------------

    # 2. get ALL users and filter out the bots so we only have _real_ users ✅
    humans = channel.get_users(
        client=client,
        channel_id=channel_id
    )
    # logger.info(humans)

    # get a random number of users based on the participants value
    member_range = helper.parse_range(num_participants)
    if len(humans) > member_range["min"]:
        participants = random.sample(humans, random.randrange(member_range["min"], member_range["max"]))
    else:
        participants = random.sample(humans, len(humans))

    # ---------------------------------------

    # 3. Update the channel topic and description if required
    logger.info(f"CHANNEL INFO: {channel_info}")
    if channel_purpose and channel_info["purpose"]["value"] != channel_purpose:
        channel.set_purpose(
            client=client,
            channel_id=channel_id,
            purpose=channel_purpose
        )
    
    if channel_topic and channel_info["topic"]["value"] != channel_topic:
        channel.set_topic(
            client=client,
            channel_id=channel_id,
            topic=channel_topic
        )
    
    # ----------------------------------------

    # 4. Update/create the canvas if required
    canvas_result = "Not selected"
    if canvas: 
        loading_view = helper.loading_formatter(
            posts="Calculating...",
            replies="Calculating...",
            canvas="Generating...",
            current="Designing canvas"
        )
        client.views_update(view_id=view_id, view=loading_view)

        # 4a. select up to 5 random users to show up as mentions in the canvas
        if len(participants) > 5:
            # reduce this to 5 users from the original set
            canvas_particpants = random.sample(humans, 5)
        else:
            canvas_particpants = participants
    
        # 4b. fetch canvas content
        canvas_content = devxp.fetch_canvas(
            channel_name=channel_info["name"],
            channel_purpose=channel_purpose,
            channel_topic=channel_topic,
            member_list=canvas_particpants
        )
        
        try:
            # 4c. Add or update the canvas
            if channel_info.get("properties", {}).get("canvas", False):
                logger.info(f"Channel {channel_id} already has a canvas")
                # do_canvas_update = True
                canvas_result = client.canvases_edit(
                    canvas_id=channel_info.get("properties", {}).get("canvas", {}).get("file_id"),
                    changes=[{"operation": "replace", "document_content": {"type": "markdown", "markdown": canvas_content["body"]}}]
                )
                # canvas_id = channel_info.get("properties", {}).get("canvas", {}).get("file_id")
            else:
                # do_canvas_update = False
                canvas_result = client.conversations_canvases_create(
                    channel_id=channel_id,
                    document_content={"type": "markdown", "markdown": canvas_content["body"]},
                    title=canvas_content["title"]
                )
                # canvas_id = canvas_result["canvas_id"]
            canvas_result = ":white_check_mark: Complete"
        except Exception as e:
            canvas_result = "Error"
            logger.error(f"Error creating canvas: {e}")
            loading_view = helper.loading_formatter(
                posts="Calculating...",
                replies="Calculating...",
                canvas=canvas_result,
                current="Generating replies"
            )
            client.views_update(view_id=view_id, view=loading_view)


    # 5. Build the conversation - one post at a time
    # determine how many posts are required
    total_posts = helper.rand_from_range_string(num_posts)
    participant_ids = [participant['id'] for participant in participants]
    if topics is None or not isinstance(topics, str):
        custom_topics = [channel_topic]
    else:
        custom_topics = helper.string_to_list(topics)
    # length = helper.rand_from_range_string(post_length)
    participant_info = []

    data_counter = {
        "posts": 0,
        "replies": 0
    }

    loading_view = helper.loading_formatter(
        posts=f"0/{total_posts}",
        replies="Calculating...",
        canvas=canvas_result,
        current="Generating messages"
    )
    client.views_update(view_id=view_id, view=loading_view)

    for _ in range(total_posts):
        if data_counter["posts"] > 0:
            loading_view = helper.loading_formatter(
                posts=f"{data_counter['posts']}/{total_posts}",
                replies=f"{data_counter['replies']} so far",
                canvas=canvas_result,
                current="Generating message"
            )
            client.views_update(view_id=view_id, view=loading_view)

        # 5a. Fetch a post
        # selecte a random user to be the author
        author = random.choice(participants)
        participant_info = {
            'id': author["id"],
            'name': author['name'],
            'real_name': author['real_name'],
            'display_name': author['profile'].get('display_name', ''),
            'title': author['profile'].get('title', ''),
            'avatar': author['profile'].get('image_192', '')
        }
        post_topic = random.choice(custom_topics)
        message_content = devxp.fetch_message(
            author=f"<@{author['id']}>",
            conversation_participants=participant_ids,
            purpose=channel_purpose,
            channel_topic=channel_topic,
            topic=post_topic,
            length=post_length,
            tone=tone,
            emoji_density=emoji_density,
            custom_prompt=custom_prompt
        )

        # some basic error handling in case the LLM throws a wobbly
        if "author" not in message_content or "message" not in message_content:
            continue

        logger.info(f"MESSAGE_CONTENT {message_content}")

        # 5b. Send the post
        message_result = message.send_message(
            client=client,
            selected_channel=channel_id,
            post=message_content,
            participant=participant_info,
            history_id=history_row["id"]
        )

        thread_messages = [{
            "text": message_result["message"]["text"],
            "author_type": "bot",
            "user": {"id": author["id"]}
        }]

        logger.info(f"MESSAGE_RESULT {message_result}")

        if "ok" in message_result and message_result["ok"]:
            data_counter["posts"] += 1
            # 5c. Attach reacjis
            message.send_reacjis(
                client=client,
                channel_id=channel_id,
                message_ts=message_result["ts"],
                reacji=message_content["reacjis"]
            )
            loading_view = helper.loading_formatter(
                posts=f"{data_counter['posts']}/{total_posts}",
                replies=f"{data_counter['replies']} so far",
                canvas=canvas_result,
                current="Generating replies"
            )
            client.views_update(view_id=view_id, view=loading_view)

        total_replies = helper.rand_from_range_string(thread_replies)

        if total_replies > 0:
            # 5c. Fetch replies
            reply_content = devxp.thread(
                description=channel_purpose,
                topic=channel_topic,
                thread=thread_messages,
                members=participant_ids,
                replies=total_replies
            )
            # 5d. Send replies
            for r in reply_content:
                logger.debug(f"REPLY: {r}")
                reply_participant = next((p for p in participants if p['id'] == r["author"]), False)
                if not reply_participant:
                    logger.error(f"Failed to find a matching conversation participant for author {r['author']}! Skipping")
                    continue

                reply_participant_info = {
                    'id': reply_participant["id"],
                    'name': reply_participant['name'],
                    'real_name': reply_participant['real_name'],
                    'display_name': reply_participant['profile'].get('display_name', ''),
                    'title': reply_participant['profile'].get('title', ''),
                    'avatar': reply_participant['profile'].get('image_192', '')
                }
                replies_result = message.send_message(
                    client=client,
                    selected_channel=channel_id,
                    post=r,
                    participant=reply_participant_info,
                    thread_ts=message_result["ts"],
                    history_id=history_row["id"]
                )

                if "ok" in replies_result and replies_result["ok"]:
                    data_counter["replies"] += 1
                    loading_view = helper.loading_formatter(
                        posts=f"{data_counter['posts']}/{total_posts}",
                        replies=f"{data_counter['replies']} so far",
                        canvas=canvas_result,
                        current="Generating replies"
                    )
                    client.views_update(view_id=view_id, view=loading_view)

                    message.send_reacjis(
                        client=client,
                        channel_id=channel_id,
                        message_ts=replies_result["ts"],
                        reacji=r["reacjis"]
                    )

    # 6. Show results modal
     # update the history for query time
    query_time = worker.get_time() - start_time
    logger.info(f"Start time = {start_time}; query time: {query_time}")
    db.update("history", {"query_time": query_time}, {"id": history_row["id"]})

    # log an entry to the analytics table
    # total_posts_sent = db.fetch_one("SELECT COUNT(*) AS total_posts_sent FROM messages WHERE history_id = %s", (history_row["id"],))["total_posts_sent"]
    total_posts_sent = data_counter["posts"] + data_counter["replies"]
    db.insert("analytics", {"user_id": current_user["id"], "messages": total_posts_sent})

    time_in_seconds = query_time/1000
    minutes, seconds = divmod(time_in_seconds, 60)
    formatted_time = f"{int(minutes):2d}:{int(seconds):02d}"
    logger.info(f"Formatted time: {formatted_time}")
    
    # Update modal to show success
    client.views_update(
        view_id=view_id,
        view={
            "type": "modal",
            "title": {
                "type": "plain_text",
                "text": "Conversation Generated"
            },
            "close": {
                "type": "plain_text",
                "text": "Close",
                "emoji": True
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
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f":stopwatch: _Conversation created in {formatted_time}_"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Posts:* {data_counter['posts']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Replies:* {data_counter['replies']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Participants:* {num_participants}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Topics:* {', '.join(custom_topics) if custom_topics else channel_topic}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"👉 *View the conversation in the <#{channel_id}> to see the results!*"
                    }
                }
            ]
        }
    )
