from flask import Flask, request
from config import logger
from user_lookup import lookup_user_by_id
from threading import Thread
from views import dashboard
import config
import pymongo

app = Flask(__name__)
app.register_blueprint(dashboard.dash, url_prefix="/dashboard")

env = config.ENV
# required = config.EXPECTED_VALUES
tasks_tbl = config.COLLECTIONS["tasks"]
started_tbl = config.COLLECTIONS["started"]
survey_tbl = config.COLLECTIONS["survey"]

# connect to DB
dbclient = pymongo.MongoClient(config.DB_CLIENT)
db = dbclient[config.DB_NAME]


# class to process the webhooks
class Process(Thread):
    def __init__(self, request, kind):
        Thread.__init__(self)
        self.request = request
        self.kind = kind

    def run(self):
        # get the payload
        payload = self.request.get_json()

        # get user_id
        user_id = payload["wm.euId"]

        # convert user_id to email
        user_email = lookup_user_by_id(env, user_id)

        if len(user_email) <= 0:
            logger.info(
                f"User email not found, most likely system was accessed without auth"
            )
            user_email = "None"
        else:
            logger.info(f"User email: {user_email}")

        # remove tabs and spaces from e-mail before adding to payload
        payload["user_email"] = user_email.replace(" ", "").replace("\t", "").lower()

        logger.debug(f"Payload with user_email: {payload}")

        # change any keys with a . to a _ because mongo doesn't like .
        updated_payload = {}
        for k, v in payload.items():
            updated_payload[k.replace(".", "_")] = payload[k]

        logger.debug(f"Updated payload: {updated_payload}")

        # default to tasks table
        collection = db[tasks_tbl]

        # if it's a task, store it in task collection
        # with proper names
        if self.kind == "task":
            collection = db[tasks_tbl]

        # if it's a SWT started event, store it in the started collection
        elif self.kind == "started":
            collection = db[started_tbl]

        # if it's a SWT started event, store it in the started collection
        elif self.kind == "survey":
            collection = db[survey_tbl]

        insert = collection.insert_one(updated_payload)
        logger.info(insert.inserted_id)
        logger.info("Successfully inserted data into DB")


# webhook routes
@app.route("/analytics/api/v1/walkmetasks", methods=["POST"])
def process_task_webhook():
    logger.info("Request received on /walkmetasks")

    # if Content-Type=application/json
    if request.is_json:
        payload = request.get_json()

        # if not all(k in payload for k in required):
        #     logger.error("Missing expected values")
        #     logger.error(payload)
        #     return ("Missing expected values", 400)

        logger.debug(payload)
        logger.debug("Processing Request")

        # process the request as a task
        thread = Process(request.__copy__(), "task")
        thread.start()

        return ("Accepted", 200)
    else:
        logger.error("Request is not json")
        return ("Invalid request", 400)


@app.route("/analytics/api/v1/walkmestarted", methods=["POST"])
def process_swt_started_webhook():
    logger.info("Request received on /walkmestarted")

    if request.is_json:
        payload = request.get_json()

        # if not all(k in payload for k in required):
        #     logger.error("Missing expected values")
        #     logger.error(payload)
        #     return ("Missing expected values", 400)

        logger.debug(payload)
        logger.info("Processing Request")

        # process the request as a started event
        thread = Process(request.__copy__(), "started")
        thread.start()

        return ("Accepted", 200)
    else:
        logger.error("Request is not json")
        return ("Invalid request", 400)


@app.route("/analytics/api/v1/walkmesurvey", methods=["POST"])
def process_swt_survey_webhook():
    logger.info("Request received on /walkmesurvey")

    if request.is_json:
        payload = request.get_json()

        logger.debug(payload)
        logger.info("Processing Request")

        # process the request as a started event
        thread = Process(request.__copy__(), "survey")
        thread.start()

        return ("Accepted", 200)
    else:
        logger.error("Request is not json")
        return ("Invalid request", 400)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
