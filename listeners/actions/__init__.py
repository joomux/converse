from slack_bolt import App
from .builder import handle_enter_builder_mode, save_builder_config, save_exit_builder_mode


def register(app: App):
    app.action("enter_builder_mode_button")(handle_enter_builder_mode)
    app.action("save_builder_config")(save_builder_config)
    app.action("save_exit_builder_mode")(save_exit_builder_mode)