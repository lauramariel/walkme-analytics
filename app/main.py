from flask import Flask, request, send_file
from config import logger
from user_lookup import lookup_user_by_id
from threading import Thread
from flask import render_template
from bson.json_util import dumps
import config
import pymongo
import datetime

app = Flask(__name__)

env = config.ENV
# required = config.EXPECTED_VALUES
tasks_tbl = config.COLLECTIONS["tasks"]
started_tbl = config.COLLECTIONS["started"]

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


# dashboard
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    started = db[started_tbl]
    completed = db[tasks_tbl]

    all_users = started.distinct("user_email")
    # all_data = list(started.find())
    # logger.debug(all_data)

    scount = started.count()
    ccount = completed.count()

    logger.debug(f"Started count: {scount}")
    logger.debug(f"Completed count: {ccount}")

    # Last 10 Started Walkthroughs
    if scount < 10:
        # if less than 10 then show all
        last_10_started = list(started.find().sort("created_at", -1))
    else:
        last_10_started = list(started.find().sort("created_at", -1).limit(10))

    # Last 10 Completed Modules
    if ccount < 10:
        # if less than 10 then show all
        last_10_completed = list(completed.find().sort("created_at", -1))
    else:
        last_10_completed = list(completed.find().sort("created_at", -1).limit(10))

    # convert timestamps and wm_env
    for i in last_10_completed:
        orig_time = i["created_at"]
        new_time = format_time(orig_time)
        i["created_at"] = new_time

        wm_env = i["wm_env"]
        env_text = format_wm_env(wm_env)
        i["wm_env"] = env_text

    for i in last_10_started:
        orig_time = i["created_at"]
        new_time = format_time(orig_time)
        i["created_at"] = new_time

        wm_env = i["wm_env"]
        env_text = format_wm_env(wm_env)
        i["wm_env"] = env_text

    # Most Popular Completed Modules
    pipeline = [{"$group": {"_id": "$oName", "count": {"$sum": 1}}}]
    agg = list(db.completed_tasks.aggregate(pipeline))
    # initialize the max
    max = 0
    max_name = 0
    for i in agg:
        if i["count"] > max:
            max_name = i["_id"]
            max = i["count"]

    return render_template(
        "index.html",
        last_10_started=last_10_started,
        last_10_completed=last_10_completed,
        total_completed=completed.count(),
        most_popular=max_name,
        most_popular_count=max,
        user_list=all_users,
    )


# convert time from epoch to UTC
def format_time(orig_time):
    epoch = orig_time / 1000
    new_time = (
        datetime.datetime.fromtimestamp(epoch)
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S")
    )
    return new_time


# convert wm_env to string value
# 0 = Prod
# 2 = Editor
# 3 = Stage
def format_wm_env(wm_env):
    wm_env_text = ""

    if wm_env == 0:
        wm_env_text = "prod"
    elif wm_env == 2:
        wm_env_text = "editor"
    elif wm_env == 3:
        wm_env_text = "stage"

    return wm_env_text


# list info for a particular user
@app.route("/dashboard/lookupuser", methods=["GET", "POST"])
def user_info():
    # started = db[started_tbl]
    completed = db[tasks_tbl]
    logger.info(f"Request form: {request.form}")

    # remove any tabs and spaces from email and make it lowercase
    user_email = request.form.get("user").replace(" ", "").replace("\t", "").lower()

    logger.info(f"Formatted: {user_email}")
    user_completed = list(
        completed.find({"user_email": user_email}).sort("created_at", -1)
    )
    # user_started = list(started.find({"user_email": user_email}).sort("created_at", -1))

    # format timestamps
    for i in user_completed:
        orig_time = i["created_at"]
        new_time = format_time(orig_time)
        i["created_at"] = new_time

    # for i in user_started:
    #     orig_time = i["created_at"]
    #     new_time = format_time(orig_time)
    #     i["created_at"] = new_time

    # render page
    return render_template(
        "user_info.html",
        user_email=user_email,
        user_completed=user_completed,
        # user_started=user_started,
    )


# export
@app.route("/dashboard/export/<collection>")
def export_files(collection):
    if collection == "started":
        logger.info("Started collection requested")
        started = db[started_tbl]
        started_data = started.find()
        with open("started.json", "w") as file:
            file.write("[")
            for document in started_data:
                # need to use json_utils because of
                # bson format returned by mongo
                file.write(dumps(document))
                file.write(",")
            file.write("]")
        logger.info("Started collection written to file")
        filename = "started.json"
        return send_file(filename, attachment_filename=filename, as_attachment=True)

    if collection == "completed":
        logger.info("Completed collection requested")
        completed = db[tasks_tbl]
        completed_data = completed.find()
        with open("completed.json", "w") as file:
            file.write("[")
            for document in completed_data:
                file.write(dumps(document))
                file.write(",")
            file.write("]")
        logger.info("Completed collection written to file")
        filename = "completed.json"
        return send_file(filename, attachment_filename=filename, as_attachment=True)
        # return Response(
        #     file,
        #     mimetype="text/plain",
        #     headers={"Content-disposition":
        #             "attachment; filename=completed.json"}
        # )


# webhook routes
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
