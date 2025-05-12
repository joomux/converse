from logging import Logger
from slack_sdk import WebClient
# from slack_sdk.errors import SlackApiError
from slack_bolt import Ack

def browse_templates_button (ack:Ack, body, client: WebClient, logger: Logger):
    ack()