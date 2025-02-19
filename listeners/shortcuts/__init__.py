from slack_bolt import App
from .thread_extend import extend_thread_callback


def register(app: App):
    app.shortcut({"callback_id": "thread_generate", "type": "message_action"})(extend_thread_callback)