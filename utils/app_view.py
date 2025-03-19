import os
import json
from logging import Logger
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from utils import builder
from datetime import datetime, timezone
from utils.database import Database, DatabaseConfig

db = Database(DatabaseConfig())

def render_app_view(client: WebClient, user_id: str, app_installed_team_id: str, view_type: str = "home", logger: Logger = None, custom_data: dict = None):
    """
    Render the app home view for a user.
    
    Args:
        client: The Slack WebClient instance
        user_id: The ID of the user whose home view to update
        app_installed_team_id: The ID of the team where the app is installed
        view_type: The type of view to render (default: "home")
                   Options: "home", "builder", "builder_step_1", etc.
        logger: Optional logger instance
        custom_data: Optional custom data to include in the view
    
    Returns:
        The response from the views_publish call or None if there was an error
    """
    try:
        if logger:
            logger.info(f"Rendering app view of type: {view_type} for user: {user_id}")
        
        # Determine the view file path based on view_type
        if view_type == "builder_step_1":
            view_path = os.path.join("block_kit", "builder_mode_step_1.json")
        elif view_type == "builder":
            view_path = os.path.join("block_kit", "builder_mode.json")
        else:  # Default to home view
            view_path = os.path.join("block_kit", "home_view.json")
        
        # Load the view JSON
        with open(view_path, 'r') as file:
            view = json.load(file)
        
        # Get user selections from the database
        config = builder.get_user_selections(user_id=user_id, app_installed_team_id=app_installed_team_id, logger=logger)
        
        # Update the view based on view_type
        if view_type == "builder_step_1":
            # Update initial values for name and customer fields
            for block in view["blocks"]:
                if logger:
                    logger.debug(f"Checking block id {block.get('block_id', None)}")
                if block.get("block_id", None) in ["name", "customer"] and config.get(block["block_id"], None) is not None:
                    if logger:
                        logger.debug(f"Setting value to {block.get('block_id', None)}")
                    block["element"]["initial_value"] = config[block["block_id"]]
            
            # Update the mode in the database
            db.update(
                "user_builder_selections", 
                {"mode": 'builder', "last_updated": datetime.now(timezone.utc)},
                {"user_id": user_id, "app_installed_team_id": app_installed_team_id}
            )

            # TODO: FIX UP THIS! MAKE IT PRETTIER AND HANDLE ALL OTHER TYPES!
            # build custom_data from selected and to-create channels and apps
            custom_data = {
                "additional_blocks": []
            }
            config = builder.get_user_selections(user_id=user_id, app_installed_team_id=app_installed_team_id, logger=logger)
            if config.get("channels", {}).get('selected'):
                custom_data["additional_blocks"].extend(_render_channels_selected(config.get("channels", {}).get('selected'), logger=logger))
            if config.get("channels", {}).get('create'):
                # custom_data["additional_blocks"] = [{"type": "section", "text": {"type": "mrkdwn", "text": f"Channel: <#{channel['channel']['id']}>"}} for channel in config["channels"]["create"]]
                custom_data["additional_blocks"].extend(_render_channels_create(config.get("channels", {}).get('create'), logger=logger))
            
            logger.info("-------------")
            logger.info(custom_data)
            logger.info("-------------")
        
        elif view_type == "builder":
            # Get builder options
            builder_options = config
            selected_values = builder_options.get("save_builder_config", [])
            
            # Update multi_static_select initial options
            for block in view["blocks"]:
                if "accessory" in block and block["accessory"].get("type") == "multi_static_select":
                    accessory = block["accessory"]
                    if selected_values:
                        # Filter the options based on selected values
                        accessory["initial_options"] = [
                            option for option in accessory["options"] if option["value"] in selected_values
                        ]
                    else:
                        # Remove initial_options if no options are selected
                        if "initial_options" in accessory:
                            del accessory["initial_options"]
            
            # Add feature-specific blocks based on selected options
            feature_blocks = {
                "option-convo": {
                    "title": "Conversations",
                    "action_id_config": "setup-convo",
                    "action_id_generate": "generate-convo"
                },
                "option-channels": {
                    "title": "Channels",
                    "action_id_config": "setup-channels",
                    "action_id_generate": "generate-channels"
                },
                "option-canvas": {
                    "title": "Canvas",
                    "action_id_config": "setup-canvas",
                    "action_id_generate": "generate-canvas"
                },
                "option-apps": {
                    "title": "Apps",
                    "action_id_config": "setup-apps",
                    "action_id_generate": "generate-apps"
                }
            }
            
            # Add blocks for each selected feature
            for option, feature_info in feature_blocks.items():
                if option in selected_values:
                    view["blocks"].extend([
                        {
                            "type": "divider"
                        },
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": feature_info["title"]
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "Configure"
                                    },
                                    "value": feature_info["action_id_config"],
                                    "action_id": feature_info["action_id_config"]
                                },
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": ":sparkles: Generate"
                                    },
                                    "style": "primary",
                                    "value": feature_info["action_id_generate"],
                                    "action_id": feature_info["action_id_generate"]
                                }
                            ]
                        }
                    ])
                    if logger:
                        logger.debug(f"Added additional block for {feature_info['title']}")
        
        # Apply any custom data modifications
        if custom_data:
            # Example: Add custom blocks
            if "additional_blocks" in custom_data:
                view["blocks"].extend(custom_data["additional_blocks"])
            
            # Example: Update specific block values
            if "block_updates" in custom_data:
                for block_id, value in custom_data["block_updates"].items():
                    for block in view["blocks"]:
                        if block.get("block_id") == block_id:
                            if "element" in block and "initial_value" in block["element"]:
                                block["element"]["initial_value"] = value
        
        # Publish the view
        if logger:
            logger.debug(f"Publishing view: {json.dumps(view, indent=2)}")
        
        response = client.views_publish(user_id=user_id, view=view)
        return response
    
    except FileNotFoundError as e:
        if logger:
            logger.error(f"View file not found: {e}")
        return None
    
    except SlackApiError as e:
        if logger:
            logger.error(f"Error publishing view: {e}")
        return None
    
    except Exception as e:
        if logger:
            logger.error(f"Unexpected error rendering app view: {e}")
        return None 
    

def _render_channels_create(channels: list, logger: Logger):
    logger.info("APP HOME> RENDER CHANNELS CREATE")
    items = []
    if channels is not None:
        logger.info(channels)
        for channel_struct in channels.get("channels", []):
            channel = channel_struct.get("channel")
            if channel is not None:
                logger.info(channel)
                items.append({
                    "type": "rich_text_section",
                    "elements": [
                        {
                            "type": "text",
                            "text": f"#{channel['name']}{' (private)' if channel['is_private'] else ''}"
                        }
                    ]
                })

    wrapper = [
        {
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "*These channels will be created*"
			}
		},
        {
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f'> {channels["use_case"]}'
			}
		},
        {
        "type": "rich_text",
        "elements": [
            {
                "type": "rich_text_list",
                "style": "bullet",
                "indent": 0,
                "elements": items
            }
        ]
    }]

    return wrapper

def _render_channels_selected(channels: list, logger: Logger):
    logger.info("APP HOME> RENDER CHANNELS SELECTED")
    # return [{"type": "section", "text": {"type": "mrkdwn", "text": f"Channel: <#{channel['channel']['id']}>"}} for channel in channels]

    items = []
    if channels is not None:
        logger.info(channels)
        for channel_struct in channels:
            channel = channel_struct.get("channel")
            if channel is not None:
                logger.info(channel)
                items.append({
                    "type": "rich_text_section",
                    "elements": [
                        {
                            "type": "channel",
                            "channel_id": channel['id']
                        }
                    ]
                })

    wrapper = [
        {
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "*These channels will be available*"
			}
		},
        {
        "type": "rich_text",
        "elements": [
            {
                "type": "rich_text_list",
                "style": "bullet",
                "indent": 0,
                "elements": items
            }
        ]
    }]

    return wrapper
    