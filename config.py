import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ADMIN_SECRET = str(os.getenv("ADMIN_SECRET"))
    SECRET_KEY = str(os.getenv("SECRET_KEY"))
    ALGORITHM = str(os.getenv("ALGORITHM"))
    ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", 24))