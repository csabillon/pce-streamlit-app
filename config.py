# config.py
from dotenv import load_dotenv
import os

load_dotenv()

# CDF settings
CDF_PROJECT = os.getenv("CDF_PROJECT")
CDF_CLUSTER = os.getenv("CDF_CLUSTER", "api")

# Build URLs & scopes
BASE_URL = f"https://{CDF_CLUSTER}.cognitedata.com"
SCOPES = "delfi-sauth-cognitedata-api-audience"

# SAuth Settings
CDF_CLIENT_ID = os.getenv("CDF_CLIENT_ID")
CDF_CLIENT_SECRET = os.getenv("CDF_CLIENT_SECRET")
AUTHORITY_HOST_URI = os.getenv("AUTHORITY_HOST_URI", "https://login.microsoftonline.com")