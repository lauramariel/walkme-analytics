from flask import Flask, request
from config import logger
from user_lookup import lookup_user_by_id
from threading import Thread
import config
import pymongo

app = Flask(__name__)

env = config.ENV
# required = config.EXPECTED_VALUES
tasks_tbl = config.COLLECTIONS["tasks"]
started_tbl = config.COLLECTIONS["started"]

# connect to DB
dbclient = pymongo.MongoClient(config.DB_CLIENT)
db = dbclient[config.DB_NAME]


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
        logger.info(f"User email: {user_email}")

        payload["user_email"] = user_email
        logger.debug(f"Payload with user_email: {payload}")

        # change any keys with a . to a _ because mongo doesn't like .
        updated_payload = {}
        for k, v in payload.items():
            updated_payload[k.replace(".", "_")] = payload[k]

        logger.debug(f"Updated payload: {updated_payload}")

        # if it's a task, store it in task collection
        # with proper names
        if self.kind == "task":
            collection = db[tasks_tbl]
            insert = collection.insert_one(updated_payload)
            logger.info(insert.inserted_id)

        # if it's a SWT started event, store it in the started collection
        elif self.kind == "started":
            collection = db[started_tbl]
            insert = collection.insert_one(updated_payload)
            logger.info(insert.inserted_id)

        logger.info("Successfully inserted data into DB")


@app.route("/analytics/api/v1/walkmetasks", methods=["POST"])
def process_task_webhook():
    logger.info("Request received")

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
    logger.info("Request received")

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


if __name__ == "__main__":
    app.run(host="0.0.0.0")
