from sqlalchemy import create_engine, Column, Integer, String, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the base class for declarative models
Base = declarative_base()

class ConversationDefinition(Base):
    __tablename__ = 'conversation_definitions'

    id = Column(Integer, primary_key=True)
    company_name = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=False)
    topics = Column(JSON, nullable=True)  # Store topics as a JSON array
    custom_prompt = Column(Text, nullable=True)
    num_participants = Column(Integer, nullable=False)
    num_posts = Column(Integer, nullable=False)
    post_length = Column(String(50), nullable=False)
    tone = Column(String(50), nullable=False)
    emoji_density = Column(String(50), nullable=False)
    thread_replies = Column(String(50), nullable=False)

# Database connection setup
DATABASE_URL = "postgresql://username:password@localhost/dbname"  # Update with your database credentials
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

# Create a session factory
Session = sessionmaker(bind=engine)

class ConversationCRUD:
    def __init__(self):
        self.session = Session()

    def create_conversation(self, conversation_data):
        conversation = ConversationDefinition(**conversation_data)
        self.session.add(conversation)
        self.session.commit()
        return conversation

    def read_conversation(self, conversation_id):
        return self.session.query(ConversationDefinition).filter_by(id=conversation_id).first()

    def update_conversation(self, conversation_id, updated_data):
        conversation = self.read_conversation(conversation_id)
        if conversation:
            for key, value in updated_data.items():
                setattr(conversation, key, value)
            self.session.commit()
            return conversation
        return None

    def delete_conversation(self, conversation_id):
        conversation = self.read_conversation(conversation_id)
        if conversation:
            self.session.delete(conversation)
            self.session.commit()
            return True
        return False

# Example usage
if __name__ == "__main__":
    crud = ConversationCRUD()
    # Example of creating a conversation
    new_conversation = crud.create_conversation({
        "company_name": "Example Corp",
        "industry": "Technology",
        "topics": ["AI", "Machine Learning"],
        "custom_prompt": "Generate a conversation about AI advancements.",
        "num_participants": 5,
        "num_posts": 10,
        "post_length": "Medium",
        "tone": "Casual",
        "emoji_density": "Average",
        "thread_replies": "3-5"
    })
    print(f"Created conversation with ID: {new_conversation.id}")