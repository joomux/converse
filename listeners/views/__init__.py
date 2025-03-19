from slack_bolt import App
from .channels import create_channels, select_channels, reload_app_home



def register(app: App):
    app.view("channel_creator_submission")(create_channels)
    app.view("channels_selected")(select_channels)
    app.view_closed("modal_channel_creater_result")(reload_app_home)