"""
# Create a new conversation
conv = Conversation(channel_id="C927539478", channel_name="#my-channel-name")
conv.set_channel_topic("Topic for the channel")
conv.set_channel_description("Description for the channel")

# Add apps
conv.add_app(app_id=123, name="App Name", frequency="few")

# Set canvas
conv.set_canvas(True)

# Set conversation parameters
conv.set_topics(["topic 1", "topic 2"])
conv.set_custom_prompt("Custom prompt for the conversation")
conv.set_participants("2-5")
conv.set_posts("5-10")
conv.set_post_length("medium")
conv.set_replies("5-10")
conv.set_tone("technical")
conv.set_emoji("few")

# Get the dictionary representation
conv_dict = conv.to_dict()
"""

import json

class Conversation:
    def __init__(self, channel_id=None, channel_name=None, channel_topic=None, channel_description=None):
        # Channel information
        self._channel = {
            "id": channel_id,
            "name": channel_name,
            "topic": channel_topic,
            "description": channel_description
        }
        
        # Apps list
        self._apps = []
        
        # Canvas flag
        self._canvas = False
        
        # Conversation parameters
        self._conversation = {
            "topics": [],
            "custom_prompt": None,
            "participants": None,
            "posts": None,
            "post_length": None,
            "replies": None,
            "tone": None,
            "emoji": None
        }
    
    # Channel getters and setters
    def set_channel_id(self, channel_id):
        self._channel["id"] = channel_id
        
    def get_channel_id(self):
        return self._channel["id"]
        
    def set_channel_name(self, channel_name):
        self._channel["name"] = channel_name
        
    def get_channel_name(self):
        return self._channel["name"]
        
    def set_channel_topic(self, channel_topic):
        self._channel["topic"] = channel_topic
        
    def get_channel_topic(self):
        return self._channel["topic"]
        
    def set_channel_description(self, channel_description):
        self._channel["description"] = channel_description
        
    def get_channel_description(self):
        return self._channel["description"]
    
    # Apps methods
    def add_app(self, app_id=None, name=None, icon_url=None, frequency=None, block_kit=None):
        app = {
            "id": app_id,
            "name": name,
            "icon_url": icon_url,
            "frequency": frequency,
            "block_kit": block_kit
        }
        self._apps.append(app)
        
    def get_apps(self):
        return self._apps
    
    def clear_apps(self):
        self._apps = []
    
    def get_app(self, app_id=None, name=None):
        """
        Get a single app by ID or name.
        
        Args:
            app_id: The ID of the app to find
            name: The name of the app to find
            
        Returns:
            The app dictionary if found, None otherwise
        """
        if app_id is not None:
            for app in self._apps:
                if app.get("id") == app_id:
                    return app
        
        if name is not None:
            for app in self._apps:
                if app.get("name") == name:
                    return app
        
        return None
    
    # Canvas getters and setters
    def set_canvas(self, canvas):
        self._canvas = bool(canvas)
        
    def get_canvas(self):
        return self._canvas
    
    # Conversation parameters getters and setters
    def set_topics(self, topics):
        if isinstance(topics, list):
            self._conversation["topics"] = topics
        elif isinstance(topics, str):
            self._conversation["topics"] = topics.split(',')
        else:
            self._conversation["topics"] = [topics] if topics else []
        
    def get_topics(self):
        return self._conversation["topics"]
        
    def set_custom_prompt(self, custom_prompt):
        self._conversation["custom_prompt"] = custom_prompt
        
    def get_custom_prompt(self):
        return self._conversation["custom_prompt"]
        
    def set_participants(self, participants):
        self._conversation["participants"] = participants
        
    def get_participants(self):
        return self._conversation["participants"]
        
    def set_posts(self, posts):
        self._conversation["posts"] = posts
        
    def get_posts(self):
        return self._conversation["posts"]
        
    def set_post_length(self, post_length):
        self._conversation["post_length"] = post_length
        
    def get_post_length(self):
        return self._conversation["post_length"]
        
    def set_replies(self, replies):
        self._conversation["replies"] = replies
        
    def get_replies(self):
        return self._conversation["replies"]
        
    def set_tone(self, tone):
        self._conversation["tone"] = tone
        
    def get_tone(self):
        return self._conversation["tone"]
        
    def set_emoji(self, emoji):
        self._conversation["emoji"] = emoji
        
    def get_emoji(self):
        return self._conversation["emoji"]
    
    # Method to convert the class to a dictionary
    def to_dict(self):
        """
        Convert the class to a dictionary, removing None values.
        """
        # Remove None values from channel dict
        channel = {k: v for k, v in self._channel.items() if v is not None}
        
        # Remove None values from conversation dict
        conversation = {}
        for k, v in self._conversation.items():
            if v is not None and (not isinstance(v, list) or len(v) > 0):
                conversation[k] = v
        
        return {
            "channel": channel,
            "apps": self._apps,
            "canvas": self._canvas,
            "conversation": conversation
        }
    
    def format(self):
        """
        Returns a dictionary in the exact format as originally specified,
        including all fields even if they are None.
        """
        return {
            "channel": {
                "id": self._channel["id"],
                "name": self._channel["name"],
                "topic": self._channel["topic"],
                "description": self._channel["description"]
            },
            "apps": self._apps,
            "canvas": self._canvas,
            "conversation": {
                "topics": self._conversation["topics"],
                "custom_prompt": self._conversation["custom_prompt"],
                "participants": self._conversation["participants"],
                "posts": self._conversation["posts"],
                "post_length": self._conversation["post_length"],
                "replies": self._conversation["replies"],
                "tone": self._conversation["tone"],
                "emoji": self._conversation["emoji"]
            }
        }
    
    # Method to create a Conversation from a dictionary
    @classmethod
    def from_dict(cls, data):
        conversation = cls()
        
        # Set channel data
        if "channel" in data:
            channel = data["channel"]
            if "id" in channel:
                conversation.set_channel_id(channel["id"])
            if "name" in channel:
                conversation.set_channel_name(channel["name"])
            if "topic" in channel:
                conversation.set_channel_topic(channel["topic"])
            if "description" in channel:
                conversation.set_channel_description(channel["description"])
        
        # Set apps
        if "apps" in data and isinstance(data["apps"], list):
            for app in data["apps"]:
                conversation.add_app(
                    app_id=app.get("id"),
                    name=app.get("name"),
                    icon_url=app.get("icon_url"),
                    frequency=app.get("frequency"),
                    block_kit=app.get("block_kit")
                )
        
        # Set canvas
        if "canvas" in data:
            conversation.set_canvas(data["canvas"])
        
        # Set conversation parameters
        if "conversation" in data:
            conv = data["conversation"]
            if "topics" in conv:
                conversation.set_topics(conv["topics"])
            if "custom_prompt" in conv:
                conversation.set_custom_prompt(conv["custom_prompt"])
            if "participants" in conv:
                conversation.set_participants(conv["participants"])
            if "posts" in conv:
                conversation.set_posts(conv["posts"])
            if "post_length" in conv:
                conversation.set_post_length(conv["post_length"])
            if "replies" in conv:
                conversation.set_replies(conv["replies"])
            if "tone" in conv:
                conversation.set_tone(conv["tone"])
            if "emoji" in conv:
                conversation.set_emoji(conv["emoji"])
        
        return conversation
    
    def to_json(self, indent=2):
        """
        Export the Conversation object as a JSON string.
        
        Args:
            indent: Number of spaces for indentation in the JSON output (default: 2)
            
        Returns:
            A JSON string representation of the conversation
        """
        return json.dumps(self.to_dict(), indent=indent)
    
    def save_to_json_file(self, filename, indent=2):
        """
        Save the Conversation object to a JSON file.
        
        Args:
            filename: Path to the file where JSON should be saved
            indent: Number of spaces for indentation in the JSON output (default: 2)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filename, 'w') as f:
                f.write(self.to_json(indent=indent))
            return True
        except Exception as e:
            print(f"Error saving to file: {e}")
            return False
    
    @classmethod
    def from_json(cls, json_str):
        """
        Create a Conversation object from a JSON string.
        
        Args:
            json_str: JSON string representation of a conversation
            
        Returns:
            A new Conversation instance
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None
    
    @classmethod
    def load_from_json_file(cls, filename):
        """
        Load a Conversation object from a JSON file.
        
        Args:
            filename: Path to the JSON file
            
        Returns:
            A new Conversation instance, or None if loading fails
        """
        try:
            with open(filename, 'r') as f:
                json_str = f.read()
            return cls.from_json(json_str)
        except Exception as e:
            print(f"Error loading from file: {e}")
            return None