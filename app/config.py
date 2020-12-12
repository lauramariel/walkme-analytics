from google.cloud import secretmanager
import logging
import json

logger = logging.getLogger("gunicorn.error")
logger.setLevel(logger.level)

ENV = "prod"

# Set up secrets
SECRET_CLIENT = secretmanager.SecretManagerServiceClient()
SECRET_NAME = "wmanalytics"
SECRET_VERSION = 3
PROJECT = "nutanix-expo"
PATH = f"projects/{PROJECT}/secrets/{SECRET_NAME}/versions/{SECRET_VERSION}"
SECRET_RESPONSE = SECRET_CLIENT.access_secret_version(request={"name": PATH})
# Load the secrets as JSON
SECRETS = json.loads(SECRET_RESPONSE.payload.data.decode("UTF-8"))

# DB info
MONGO_CREDS = SECRETS["mongo_creds"]
MONGO_URL = SECRETS["mongo_url"]
DB_NAME = "wm_analytics"
DB_CLIENT = (
    f"mongodb+srv://{MONGO_CREDS}@{MONGO_URL}/{DB_NAME}?retryWrites=true&w=majority"
)
COLLECTIONS = {
    "started": "started_walkthroughs",
    "tasks": "completed_tasks",
    "survey": "survey_results",
}

# Configure Intercom Endpoints
INTERCOM_ENDPOINTS = {
    "contacts": "https://api.intercom.io/contacts",
    "visitors": "https://api.intercom.io/visitors",
    "companies": "https://api.intercom.io/companies",
    "attibutes": "https://api.intercom.io/data_attributes",
    "tags": "https://api.intercom.io/tags",
    "segments": "https://api.intercom.io/segments",
    "notes": "https://api.intercom.io/notes",
    "events": "https://api.intercom.io/events",
    "counts": "https://api.intercom.io/counts",
    "conversations": "https://api.intercom.io/conversations",
    "admins": "https://api.intercom.io/admins",
    "teams": "https://api.intercom.io/teams",
}

INTERCOM_SEARCH = INTERCOM_ENDPOINTS["contacts"] + "/search"
INTERCOM_HEADERS = {
    "Accept": "application/json",
    "Authorization": f"Bearer {SECRETS['ic_key_stage']}",
}
INTERCOM_QUERY_TEMPLATE = {
    "query": {"field": "email", "operator": "=", "value": "REPLACEME"}
}
