from slack_bolt import App
from .channels import create_channels, select_channels



def register(app: App):
    app.view("channel_creator_submission")(create_channels)
    app.view("channels_selected")(select_channels)