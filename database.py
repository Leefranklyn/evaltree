from mongoengine import connect
import os
from dotenv import load_dotenv

load_dotenv()

def connect_db():
    connect(
        db="quiz_db",
        host=os.getenv("DATABASE_URL")
    )