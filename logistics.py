from slack_sdk.errors import SlackApiError
from objects import Database, DatabaseConfig
from typing import Dict, Any
import logging
import time
import worker

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def _send_conversation(client, selected_channel: str, post: list|dict, participant_info: dict):
    db = Database(DatabaseConfig())

    post_results = []
    reply_results = []

    if isinstance(post, list):
        for item in post:
            temp_result = _send_conversation(client, selected_channel, item, participant_info)
            post_results.append(temp_result["post_results"])
            reply_results.append(temp_result["reply_results"])
        return {
            "post_results": post_results,
            "reply_results": reply_results
        }

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
        # main_post = client.chat_postMessage(
        #     channel=selected_channel,
        #     text=post["message"],
        #     username=participant["real_name"],
        #     icon_url=participant["avatar"],
        #     metadata={
        #         "event_type": "converse_message_posted",
        #         "event_payload": {
        #             "actor_id": participant["id"],
        #             "actor_name": participant["real_name"],
        #             "avatar": participant["avatar"]
        #         }
        #     }
        # )

        logger.debug(f"POSTING {post}")
        main_post = send_message(
            client=client,
            selected_channel=selected_channel,
            post=post,
            participant=participant,
            thread_ts=False,
            history_id=post["history"]["id"]
        )

        post_results.append(main_post)

        if "reacjis" in post and post["reacjis"]:
            for reaction in post["reacjis"]:
                try:
                    client.reactions_add(
                        channel=selected_channel,
                        timestamp=main_post["ts"],
                        name=reaction.strip(':')
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

                # reply_post = client.chat_postMessage(
                #     channel=selected_channel,
                #     thread_ts=main_post["ts"],
                #     text=reply["message"],
                #     username=reply_participant["real_name"],
                #     icon_url=reply_participant["avatar"],
                #     metadata={
                #         "event_type": "converse_reply_posted",
                #         "event_payload": {
                #             "actor_id": reply_participant["id"],
                #             "actor_name": reply_participant["real_name"],
                #             "avatar": reply_participant["avatar"]
                #         }
                #     }
                # )

                reply_post = send_message(
                    client=client,
                    selected_channel=selected_channel,
                    post=reply,
                    participant=reply_participant,
                    thread_ts=main_post["ts"],
                    history_id=post["history"]["id"]
                )

                reply_results.append(reply_post)

                if "reacjis" in reply and reply["reacjis"]:
                    for reaction in reply["reacjis"]:
                        try:
                            client.reactions_add(
                                channel=selected_channel,
                                timestamp=reply_post["ts"],
                                name=reaction.strip(':')
                            )
                        except Exception as e:
                            logger.error(f"Error adding reaction {reaction} to reply post {reply_post['ts']}: {e}")
                            continue

        # Add slight delay between posts to avoid rate limits
        time.sleep(1)

    except SlackApiError as e:
        logger.error(f"Error posting message to channel: {e}")
    
    return {
        "post_results": post_results,
        "reply_results": reply_results
    }


def _send_canvas(client: dict, channel: str, content: str, do_update: bool = False):
    channel_info = client.conversations_info(channel=channel, include_num_members=True)
    channel_details = channel_info["channel"]
    if do_update:
        canvas_result = client.canvases_edit(
            canvas_id=channel_details.get("properties", {}).get("canvas", {}).get("file_id"),
            changes=[{"operation": "replace", "document_content": {"type": "markdown", "markdown": content["body"]}}]
        )
        canvas_id = channel_details.get("properties", {}).get("canvas", {}).get("file_id")
    else:
        canvas_result = client.conversations_canvases_create(
            channel_id=channel,
            document_content={"type": "markdown", "markdown": content["body"]}
        )
        canvas_id = canvas_result["canvas_id"]
    return canvas_id

def _send_channels(client: dict, user_id: str, channels_list: list):
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
            # dm_result = client.chat_postMessage(
            #     channel=user_id,
            #     text=f"✨ Created channel <#{channel_created['channel']['id']}>\n" + 
            #         (f"> {channel_def.get('description', 'No description provided')}")
            # )

            created_channels.append(channel_created["channel"]["id"])
            
        except SlackApiError as e:
            logger.error(f"Error creating channel {channel_def['name']}: {e}")
    
    return created_channels


def send_message(client, selected_channel: str, post: dict, participant: dict = None, thread_ts: str = False, history_id: int = None):
    event_type = "converse_reply_posted" if thread_ts else "converse_message_posted"
    db = Database(DatabaseConfig())
    try:
        if participant:
            if thread_ts:
                api_result = client.chat_postMessage(
                    channel=selected_channel,
                    text=post["message"],
                    username=participant["real_name"],
                    icon_url=participant["avatar"],
                    thread_ts=thread_ts if thread_ts else False,
                    metadata={
                        "event_type": event_type,
                        "event_payload": {
                            "actor_id": participant["id"],
                            "actor_name": participant["real_name"],
                            "avatar": participant["avatar"]
                        }
                    }
                )
            else:
                api_result = client.chat_postMessage(
                    channel=selected_channel,
                    text=post["message"],
                    username=participant["real_name"],
                    icon_url=participant["avatar"],
                    metadata={
                        "event_type": event_type,
                        "event_payload": {
                            "actor_id": participant["id"],
                            "actor_name": participant["real_name"],
                            "avatar": participant["avatar"]
                        }
                    }
                )

            # Log the message to the database
            message_ts = api_result["ts"]
            db.insert("messages", {
                "message_ts": message_ts,
                "history_id": history_id if history_id else 0
            })
            return api_result
        else:
            api_result = client.chat_postMessage(
                channel=selected_channel,
                text=post["message"],
                thread_ts=thread_ts if thread_ts else False,
            )
            return api_result

    except SlackApiError as e:
        logger.error(f"Error sending message: {e}")
    except Exception as e:
        logger.error(f"Error in send_message: {e}")
    

def send_reacjis(client, channel_id, message_ts: str, reacji):
    if not isinstance(reacji, list):
        reacji = [reacji]
    
    for r in reacji:
        try:
            client.reactions_add(
                channel=channel_id,
                timestamp=message_ts,
                name=r.strip(':')
            )
        except Exception as e:
            logger.error(f"Error adding reaction {reacji} to post {message_ts}: {e}")
            continue