from logging import Logger
from utils import user
from utils.database import Database, DatabaseConfig
from ai import devxp
import random
from slack_bolt import Say

db = Database(DatabaseConfig())

def extend_thread(client, member_id, channel_id, message_ts, say: Say, logger: Logger):
    current_user = user.get_user(client, member_id, logger=logger)

    # Prep the message history log
    history_entry = {
        "conversation_id": None,
        "channel_id": channel_id,
        "user_id": current_user["id"]
    }
    history_row = db.insert("history", history_entry)
    start_time = user.get_time()

    main_ts = message_ts

    # temp_message = logistics.send_message(
    #     client=client,
    #     selected_channel=channel_id,
    #     post={"message": "Generating conversations..."},
    #     thread_ts=main_ts
    # )

    # Get thread and members
    thread = client.conversations_replies(channel=channel_id, ts=main_ts, include_all_metadata=True)
    member_ids = client.conversations_members(channel=channel_id)["members"]

    # Get human members
    human_members = [
        member_id for member_id in member_ids
        if not client.users_info(user=member_id)["user"]["is_bot"]
    ]

    # Limit the thread to 5 members
    conversation_participants = random.sample(human_members, min(len(human_members), 5))

    logger.info(thread)
    thread_messages = []

    for message in thread["messages"]:
        logger.info(message)
        author_id = ""
        if "subtype" in message and message["subtype"] == "bot_message":
            logger.info(f"Bot message detected: {message['text']}")
            if message.get("metadata", {}).get("event_type") in ["converse_message_posted", "converse_reply_posted"]:
                author_id = message["metadata"]["event_payload"]["actor_id"]
            thread_messages.append({
                "text": message["text"],
                "author_type": "bot",
                "user": {"id": author_id}
            })
        else:
            thread_messages.append({
                "text": message["text"],
                "author_type": "user",
                "user": {"id": message["user"]}
            })

    logger.info(thread_messages)

    # Get channel info
    channel = client.conversations_info(channel=channel_id)
    logger.info(channel)

    # Pass messages to the AI as context and get additional replies
    new_replies = devxp.thread(
        description=channel["description"],
        topic=channel["topic"],
        thread=thread_messages,
        members=human_members
    )

    for reply in new_replies:
        reply["author"] = ''.join(c for c in reply["author"] if c.isalnum())
        logger.info(f"Getting user info for {reply['author']}")
        author_full_info = client.users_info(user=reply["author"])
        reply_post = {"message": reply["message"]}
        author = {
            "id": reply["author"],
            "real_name": author_full_info["user"].get('real_name', ''),
            "avatar": author_full_info["user"]["profile"].get('image_192', '')
        }
        try:
            # reply_result = logistics.send_message(
            #     client=client,
            #     selected_channel=channel_id,
            #     post=reply_post,
            #     participant=author,
            #     thread_ts=main_ts,
            #     history_id=history_row["id"]
            # )

            reply_result = say(
                channel=channel_id,
                thread_ts=main_ts,
                text=reply_post["message"],
                username=author["real_name"],
                icon_url=author["avatar"],
                metadata={
                    "event_type": "converse_reply_posted",
                    "event_payload": {
                        "actor_id": author["id"],
                        "actor_name": author["real_name"],
                        "avatar": author["avatar"]
                    }
                }
            )

            if "reacjis" in reply:
                # logistics.send_reacjis(
                #     client=client,
                #     channel_id=channel_id,
                #     message_ts=reply_result["ts"],
                #     reacji=reply["reacjis"]
                # )
                reacji = reply["reacjis"]
                if not isinstance(reacji, list):
                    reacji = [reacji]
                
                for r in reacji:
                    try:
                        client.reactions_add(
                            channel=channel_id,
                            timestamp=reply_result["ts"],
                            name=r.strip(':')
                        )
                    except Exception as e:
                        logger.error(f"Error adding reaction {reacji} to post {reply_result['ts']}: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error sending reply: {e}")

    # Delete the temp message
    # client.chat_delete(channel=temp_message["channel"], ts=temp_message["ts"])

    # Update the history for query time
    query_time = user.get_time() - start_time
    logger.info(f"Start time = {start_time}; query time: {query_time}")
    db.update("history", {"query_time": query_time}, {"id": history_row["id"]})

    # Log an entry to the analytics table
    total_posts_sent = db.fetch_one("SELECT COUNT(*) AS total_posts_sent FROM messages WHERE history_id = %s", (history_row["id"],))["total_posts_sent"]
    db.insert("analytics", {"user_id": current_user["id"], "messages": total_posts_sent})