from flask import Flask, request, send_file
from config import logger
from user_lookup import lookup_user_by_id
from threading import Thread
from flask import render_template
from bson.json_util import dumps
import config
import pymongo
from datetime import datetime, timezone
import requests

app = Flask(__name__)

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

        # track intercom event for surveys in staging only
        if (
            "staging" in updated_payload.get("ctx_location_hostname")
            and self.kind == "survey"
        ):
            logger.info(f"Calling get_intercom_id with {user_id} {user_email}")
            intercom_id = get_intercom_id(marketo_id=user_id, email=user_email)
            logger.info(f"intercom_id: {intercom_id}")
            track_intercom_event(intercom_id, user_id, updated_payload)


def track_intercom_event(intercom_id, marketo_id, event_data):
    timestamp_now = int(datetime.now(timezone.utc).timestamp())
    activated_body = {
        "role": "user",
        "external_id": marketo_id,
        "last_seen_at": timestamp_now,
        "custom_attributes": {"activated": True},
    }
    survey_question = event_data.get("oName")
    survey_response = event_data.get("value")
    xp = event_data.get("ctx_location_hostname").split(".")[0][
        :-10
    ]  # change this to the constant the cloud engine uses

    user_update_url = config.INTERCOM_ENDPOINTS["contacts"] + f"/{intercom_id}"
    event_track_url = config.INTERCOM_ENDPOINTS["events"]
    event_track_body = {
        "event_name": "Survey Response Recorded",
        "created_at": timestamp_now,
        "user_id": marketo_id,
        "metadata": {
            "Question": survey_question,
            "Answer": survey_response,
            "Experience": xp,
        },
    }

    user_response = requests.put(
        user_update_url, headers=config.INTERCOM_HEADERS, json=activated_body
    )

    logger.info(
        f"Intercom response for user_update: {user_response} {user_response.text}"
    )
    track_response = requests.post(
        event_track_url, headers=config.INTERCOM_HEADERS, json=event_track_body
    )

    logger.info(
        f"Intercom response for track_event: {track_response} {track_response.text}"
    )

    return user_response.ok and track_response.ok


def get_intercom_id(marketo_id=None, email=None):
    """
    Searches for a user by either marketo_id or email (whichever is provided)
    Marketo_id overrides email if both are provided
    """
    if not (marketo_id or email):
        logger.info(
            f"intercom.get_intercom_id - No marketo_id "
            + f"or e-mail provided - returning None"
        )
        return None
    ic_query = dict(config.INTERCOM_QUERY_TEMPLATE)
    if email:
        ic_query["query"]["field"] = "email"
        ic_query["query"]["value"] = email

    if marketo_id:
        ic_query["query"]["field"] = "external_id"
        ic_query["query"]["value"] = marketo_id
    logger.info(f"Querying intercom: {ic_query}")
    # Execute the query
    ic_response = requests.post(
        config.INTERCOM_SEARCH, headers=config.INTERCOM_HEADERS, json=ic_query
    )
    logger.info(f"Intercom response: {ic_response} {ic_response.text}")
    if ic_response.ok:
        ic_json = ic_response.json()
        if ic_json["total_count"] > 0:
            intercom_id = ic_json["data"][0]["id"]
            logger.info(f"Found user: {marketo_id}{email} => {intercom_id}")
            return intercom_id
    return None


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


# dashboard
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    started = db[started_tbl]
    completed = db[tasks_tbl]
    survey = db[survey_tbl]

    all_users = started.distinct("user_email")
    # all_data = list(started.find())
    # logger.debug(all_data)

    scount = started.count()
    ccount = completed.count()
    svcount = survey.find(
        {"oName": "How was your Test Drive experience today?"}
    ).count()

    logger.debug(f"Surveys Taken: {svcount}")
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
        surveycount=svcount,
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


@app.route("/dashboard/surveys", methods=["GET", "POST"])
def survey_results():
    # started = db[started_tbl]
    surveys = db[survey_tbl]

    # returns a list of dicts
    survey_results = list(surveys.find().sort("created_at", -1).limit(100))

    # format timestamps and hostname by updating the dictionary
    for i in survey_results:
        orig_time = i["created_at"]
        new_time = format_time(orig_time)
        i["created_at"] = new_time

        orig_hostname = i["ctx_location_hostname"]
        new_hostname = orig_hostname.split(".")[0]
        i["ctx_location_hostname"] = new_hostname

    # render page
    return render_template("survey.html", survey_results=survey_results)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
