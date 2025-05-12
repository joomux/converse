from slack_sdk import WebClient
from slack_bolt import Ack
from logging import Logger
import json
import os

def app_home_popup(ack: Ack, body, client: WebClient, logger: Logger):
    ack()
    # view_path = os.path.join("block_kit", "app_home_preview_modal.json")
    # with open(view_path, 'r') as file:
    #     app_home_preview_modal = json.load(file)

    bot = client.auth_test()
    app_home_preview_modal = {
        "type": "modal",
        "title": {
            "type": "plain_text",
            "text": "Converse 2",
            "emoji": True
        },
        "close": {
            "type": "plain_text",
            "text": "Close",
            "emoji": True
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*:horse: Whoa... slow down a second*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "We :heart: your enthusiasim, but this is not quite ready yet!"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Use the _Add Conversation_ global shortcut; the _Extend Thread_ message action, or just mention <@{bot['user_id']}> app in your channel!"
                }
            },
		{
			"type": "divider"
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": ":mega: *Feedback*"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "Join <https://salesforce.enterprise.slack.com/archives/C078C6K0S9H|#proj-slack-demo-generator> to share your feedback and ideas!"
			}
		}
        ]
    }
    
    trigger_id = body["trigger_id"]
    client.views_open(trigger_id=trigger_id, view=app_home_preview_modal)