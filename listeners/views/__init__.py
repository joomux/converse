from slack_bolt import App
from .channels import create_channels



def register(app: App):
    app.view("channel_creator_submission")(create_channels)