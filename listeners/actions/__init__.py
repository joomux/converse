from slack_bolt import App
from .builder import handle_enter_builder_mode, save_builder_config, save_exit_builder_mode, builder_step_one, basic_update, builder_step_two
from .channels import open_channel_creator, open_channel_selector
from .ai_designer import ai_designer
from .conversation import channel_designer


def register(app: App):
    app.action('builder_step_one')(builder_step_one)
    app.action("enter_builder_mode_button")(handle_enter_builder_mode)
    app.action("save_builder_config")(save_builder_config)
    app.action("save_exit_builder_mode")(save_exit_builder_mode)
    app.action("channels_create")(open_channel_creator)
    app.action("channels_select")(open_channel_selector)
    app.action("channel_build_with_ai")(ai_designer)
    app.action("channel_designer")(channel_designer)
    app.action("name_update")(basic_update)
    app.action("customer_name_update")(basic_update)
    app.action("clear")(save_exit_builder_mode)
    app.action("builder_step_two")(builder_step_two)