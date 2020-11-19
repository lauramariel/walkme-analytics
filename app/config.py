from google.cloud import secretmanager
import logging
import json

logger = logging.getLogger("gunicorn.error")
logger.setLevel(logger.level)

ENV = "prod"

# Set up secrets
SECRET_CLIENT = secretmanager.SecretManagerServiceClient()
SECRET_NAME = "wmanalytics"
SECRET_VERSION = 1
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
