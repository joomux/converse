import os
import logging
from slack_bolt import App, Ack
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_bolt.oauth.oauth_flow import OAuthFlow
from slack_sdk.oauth.installation_store.sqlalchemy import SQLAlchemyInstallationStore
from slack_sdk.oauth.state_store.sqlalchemy import SQLAlchemyOAuthStateStore
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.flask import SlackRequestHandler
import sqlalchemy
from sqlalchemy.engine import Engine
from flask import Flask, request, jsonify, Response
from slack_bolt.request import BoltRequest

from listeners import register_listeners

logging.basicConfig(level=os.environ.get('LOGLEVEL', logging.DEBUG))
logger = logging.getLogger(__name__)

mode = os.environ.get("SLACK_APP_MODE", "socket").lower()

if mode != "socket":
    logger.info("NOT in socket mode! Let's go!")
    ######################################
    #
    # USE THIS FOR NON-SOCKET MODE!
    #
    database_url = os.environ["DATABASE_URL"].replace("postgres", "postgresql")

    client_id, client_secret, signing_secret = (
        os.environ["SLACK_CLIENT_ID"],
        os.environ["SLACK_CLIENT_SECRET"],
        os.environ["SLACK_SIGNING_SECRET"],
    )

    engine: Engine = sqlalchemy.create_engine(database_url)
    installation_store = SQLAlchemyInstallationStore(
        client_id=client_id,
        engine=engine,
        logger=logger
    )

    oauth_state_store = SQLAlchemyOAuthStateStore(
        expiration_seconds=120,
        engine=engine,
        logger=logger
    )

    try:
        engine.execute("SELECT COUNT(*) FROM slack_bots")
    except Exception as ralph:
        installation_store.metadata.create_all(engine)
        oauth_state_store.metadata.create_all(engine)
    
    oauth_settings = OAuthSettings(
        client_id=client_id,
        client_secret=client_secret,
        state_store=oauth_state_store,
        scopes=[
            "canvases:read",
            "canvases:write",
            "channels:history",
            "channels:join",
            "channels:manage",
            "channels:read",
            "channels:write.invites",
            "channels:write.topic",
            "chat:write",
            "chat:write.customize",
            "files:read",
            "groups:history",
            "groups:read",
            "groups:write",
            "im:history",
            "im:read",
            "mpim:history",
            "mpim:read",
            "mpim:write",
            "search:read.private",
            "users:read",
            "reactions:write",
            "commands",
            "app_mentions:read"
        ],
        redirect_uri=f"https://{os.environ['APP_DOMAIN']}/slack/oauth_redirect",
        install_page_rendering_enabled=False,
        install_path="/slack/install/"
    )

    oauth_flow = OAuthFlow(settings=oauth_settings)

    app = App(
        logger=logger,
        signing_secret=signing_secret,
        installation_store=installation_store,
        oauth_settings=oauth_settings,
        oauth_flow=oauth_flow
    )
    #
    #########################################

else: # we're in socket mode!
    # Initialization
    logger.info("IN socket mode! Let's go!")
    app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Register Listeners
register_listeners(app)

# This function serves to handle UI actions that do not need to actually do anything
@app.action("do_nothing")
def do_nothing(ack: Ack):
    ack()

logger.info("Preparing flask")
flask_app = Flask(__name__)
flask_app.config["SERVER_NAME"] = os.environ["SERVER_NAME"]
flask_app.config["PREFERRED_URL_SCHEME"] = "https"
handler = SlackRequestHandler(app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@flask_app.route("/slack/install", methods=["GET"])
def install():
    try:
        # Create a compatible request object for Bolt's OAuth flow
        bolt_request = BoltRequest(
            body=request.get_data(as_text=True) or "",
            query=request.args,
            headers=request.headers,
        )
        bolt_resp = app.oauth_flow.handle_installation(bolt_request)
        return Response(
            response=bolt_resp.body, status=bolt_resp.status, headers=bolt_resp.headers
        )
    except Exception as e:
        logging.error(f"Error handling installation: {e}")
        return "An error occurred during installation", 500

@flask_app.route("/slack/oauth_redirect", methods=["GET"])
def oauth_redirect():
    try:
        logging.info("OAuth redirect started")
        logging.info(f"Request args: {request.args}")
        result = handler.handle(request)
        logging.info(f"OAuth result: {result}")
        return result
    except Exception as e:
        logging.error(f"Error in OAuth redirect: {str(e)}", exc_info=True)
        return "An error occurred during the OAuth process", 500

import json

@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    try:
        # Test with minimal valid view structure first
        view = {
            "type": "home",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Welcome home!"
                    }
                }
            ]
        }
            
        # Publish the view
        response = client.views_publish(
            user_id=event["user"],
            view=view
        )
        
        if not response["ok"]:
            logger.error(f"Failed to publish view: {response['error']}")
            logger.error(f"View content: {json.dumps(view, indent=2)}")
            return
            
        logger.info(f"Home tab updated for user {event['user']}")

    except Exception as e:
        logger.error(f"Error updating home tab: {str(e)}", exc_info=True)

# Start Bolt app
if __name__ == "__main__":
    
    if mode == "socket":
        # Socket mode (no public endpoints needed)
        logger.info("Starting socket mode handler!")
        SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN")).start()
    else:
        # HTTP mode (requires public endpoints)
        logger.info("STARTING FLASK!")
        port = int(os.environ.get("PORT", 3000))
        flask_app.run(host="0.0.0.0", port=port)