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

def single_channel_form(ack: Ack, body, client: WebClient, view, logger: Logger, say: Say):
    # ack()
    try:
        view_path = os.path.join("block_kit", "conversation_modal.json")
        with open(view_path, 'r') as file:
            conversation_modal = json.load(file)
        
        view_id = body["view"]["id"]
        trigger_id = body["trigger_id"]
        logger.info("BODY")
        logger.info(body)
        logger.info(f"VIEW ID: {view_id}")


        channel_id = body["view"]["state"]["values"]["add_conversation_channel_selector"]["conversation_select"]["selected_conversation"]
        channel_info = client.conversations_info(channel=channel_id)
        logger.info(f"CHANNEL INFO: {channel_info}")

        conversation_modal["private_metadata"] = channel_id

        for block in conversation_modal["blocks"]:
            if block.get("block_id") == "channel_topic":
                block["element"]["placeholder"] = {"type": "plain_text", "text": channel_info["channel"]["topic"]["value"]}
                block["element"]["initial_value"] = channel_info["channel"]["topic"]["value"]
            if block.get("block_id") == "channel_description":
                block["element"]["placeholder"] = {"type": "plain_text", "text": channel_info["channel"]["purpose"]["value"]}
                block["element"]["initial_value"] = channel_info["channel"]["purpose"]["value"]

        ack(response_action="update", view=conversation_modal)
        # view = client.views_update(view_id=view_id, view=conversation_modal)
        # logger.info(f"TRIGGER ID: {trigger_id}")
        # view = client.views_push(trigger_id=trigger_id, view=conversation_modal)
    except Exception as e:
        logger.error(f"SINGLE_CHANNEL_FORM: {e}")
    
def conversation_generate(ack: Ack, body, client: WebClient, view, logger: Logger):
    logger.info("TIME TO GENERATE THE CONVERSATION!")
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
    channel_info = channel.get_info(
        client=client,
        channel_id=channel_id
    )

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
    if not channel.is_bot_in_channel(
        client=client,
        channel_id=channel_id
    ) and not channel_info["is_private"]:
        channel.add_bot_to_channel(
            client=client,
            channel_id=channel_id
        )
    else:
        # unable to add bot to channel!
        error = f"Unable to add Converse to <#{channel_id}>. If this is a private channel, please manually add Converse then try again."
    
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
    if channel_info["purpose"]["value"] != channel_purpose:
        channel.set_purpose(
            client=client,
            channel_id=channel_id,
            purpose=channel_purpose
        )
    
    if channel_info["topic"]["value"] != channel_topic:
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
                thread=message_result,
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
    total_posts_sent = db.fetch_one("SELECT COUNT(*) AS total_posts_sent FROM messages WHERE history_id = %s", (history_row["id"],))["total_posts_sent"]
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
