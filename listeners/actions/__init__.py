from slack_bolt import App
from .builder import handle_enter_builder_mode, save_builder_config, save_exit_builder_mode
from .channels import open_channel_creator
from .ai_designer import ai_designer
from .conversation import channel_designer


def register(app: App):
    app.action("enter_builder_mode_button")(handle_enter_builder_mode)
    app.action("save_builder_config")(save_builder_config)
    app.action("save_exit_builder_mode")(save_exit_builder_mode)
    app.action("setup-channels")(open_channel_creator)
    app.action("channel_build_with_ai")(ai_designer)
    app.action("channel_designer")(channel_designer)