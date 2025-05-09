import os
from slack_sdk.errors import SlackApiError
# from objects import Database, DatabaseConfig
from typing import Dict, Any
import logging
import time
# import worker
from .database import Database, DatabaseConfig

logging.basicConfig(level=os.environ.get('LOGLEVEL', logging.DEBUG))
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

        logger.info(f"SEND_CONVERSATION - main_post: {main_post}")
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
    
    logger.info(f"_SEND_CONVERSATION: {post_results}")
    return {
        "post_results": post_results,
        "reply_results": reply_results
    }

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
        import traceback
        logger.error(f"Error in send_message: {e}")
        traceback.print_exc()
    

def send_reacjis(client, channel_id, message_ts: str, reacji: str|list):
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