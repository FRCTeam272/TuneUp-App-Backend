from dotenv import load_dotenv
import os

load_dotenv()  # take environment variables from .env file
password_env = os.getenv("password", "")