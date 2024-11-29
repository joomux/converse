from slack.errors import SlackApiError
import logging
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def _send_conversation(client, selected_channel, content, participant_info):
    post_results = []
    reply_results = []
    for post in content:
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
            main_post = client.chat_postMessage(
                channel=selected_channel,
                text=post["message"],
                username=participant["real_name"],
                icon_url=participant["avatar"]
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

                    reply_post = client.chat_postMessage(
                        channel=selected_channel,
                        thread_ts=main_post["ts"],
                        text=reply["message"],
                        username=reply_participant["real_name"],
                        icon_url=reply_participant["avatar"]
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
            continue
    
    return {
        "post_results": post_results,
        "reply_results": reply_post
    }