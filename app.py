import os
import logging

from slack_bolt import App, Ack
from slack_bolt.adapter.socket_mode import SocketModeHandler

from listeners import register_listeners

logging.basicConfig(level=logging.DEBUG)

# Initialization
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Register Listeners
register_listeners(app)

# This function serves to handle UI actions that do not need to actually do anything
@app.action("do_nothing")
def do_nothing(ack: Ack):
    ack()

# Start Bolt app
if __name__ == "__main__":
    SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()