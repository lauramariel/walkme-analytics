from flask import request, send_file, Blueprint
from config import logger
from flask import render_template
from bson.json_util import dumps
import config
import pymongo
import datetime
import re

env = config.ENV
# required = config.EXPECTED_VALUES
tasks_tbl = config.COLLECTIONS["tasks"]
started_tbl = config.COLLECTIONS["started"]
survey_tbl = config.COLLECTIONS["survey"]

# connect to DB
dbclient = pymongo.MongoClient(config.DB_CLIENT)
db = dbclient[config.DB_NAME]

dash = Blueprint("dash", __name__)

# dashboard
@dash.route("/", methods=["GET", "POST"])
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
@dash.route("/dashboard/lookupuser", methods=["GET", "POST"])
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
@dash.route("/dashboard/export/<collection>")
def export_files(collection):
    # if collection == "started":
    #     logger.info("Started collection requested")
    #     started = db[started_tbl]
    #     started_data = started.find()
    #     with open("started.json", "w") as file:
    #         file.write("[")
    #         for document in started_data:
    #             # need to use json_utils because of
    #             # bson format returned by mongo
    #             file.write(dumps(document))
    #             file.write(",")
    #         file.write("]")
    #     logger.info("Started collection written to file")
    #     filename = "started.json"
    #     return send_file(filename, attachment_filename=filename, as_attachment=True)

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


@dash.route("/dashboard/surveys", methods=["GET", "POST"])
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


@dash.route("/userdash", methods=["GET", "POST"])
def userdash():
    # Check if the user is logged in
    # and if their session hash is correct
    error = None
    launch_xp = None
    user_email = "laura.jordana@nutanix.com"
    active_xps = {
        "td2": {
            "status": 100,
            "td_start": 1607639881,
            "guide": "",
            "endtime": 1607726281,
            "name": "test",
            "links": {"primary": "https://td2ugiyyx10ab.nutanixtestdrive.com/console/"},
            "friendly_name": "Nutanix Test Drive",
            "accessed": "false",
            "time_left": "2:59",
            "percent_left": 74,
        }
    }
    # list of tuples
    # [('td2', 'Nutanix Test Drive'), ('era', 'Era Test Drive') ... etc]
    all_xps = config.EXPERIENCE_SETS

    # dict of detailed xp_info
    xp_info = config.XP_INFO

    logger.info("xp_info " + str(type(xp_info)) + f"{xp_info}")
    logger.info("all_xps " + str(type(all_xps)) + f"{all_xps}")

    # get the user's completed tasks for all xps

    # db collection
    completed = db[tasks_tbl]

    # dictionary to hold the total number of tasks completed
    xp_dict = {}

    # dictionary of total number of tasks per xp
    max_tasks = {
        "td2": 9,
        "tdleap": 3,
        "xileap": 3,
        "tddata": 6,
        "nx101": 4,
        "karbon": 4,
        "calm": 4,
        "clusters": 3,
        "minehycu": 1,
        "flow": 4,
        "files": 5,
        "era": 4,
        "prism": 0,
    }

    for xp in all_xps:
        logger.info(f"Checking {xp[0]}")
        xp_name = xp[0]

        # handle granular tasks
        if xp_name == "td2":
            # look up td2-aos, td2-prismpro, td2-calm
            total = completed.aggregate(
                [
                    {
                        "$match": {
                            "user_email": user_email,
                            "oName": re.compile(
                                r"\\|td2-aos\||\|td2-prismpro\||\|td2-calm\|"
                            ),
                        }
                    },
                    {"$group": {"_id": None, "count": {"$sum": 1}}},
                ]
            )

        elif xp_name == "tddata":
            total = completed.aggregate(
                [
                    {
                        "$match": {
                            "user_email": user_email,
                            "oName": re.compile(
                                r"\\|files-tddata\||\|objects-tddata\|"
                            ),
                        }
                    },
                    {"$group": {"_id": None, "count": {"$sum": 1}}},
                ]
            )

        elif xp_name == "files":
            total = completed.aggregate(
                [
                    {
                        "$match": {
                            "user_email": user_email,
                            "oName": re.compile(r"\\|files\||\|files-tddata\|"),
                        }
                    },
                    {"$group": {"_id": None, "count": {"$sum": 1}}},
                ]
            )

        # xileap uses the same onboarding tasks as tdleap
        elif xp_name == "xileap" or xp_name == "tdleap":
            total = completed.aggregate(
                [
                    {
                        "$match": {
                            "user_email": user_email,
                            "oName": re.compile(r"\\|tdleap\|"),
                        }
                    },
                    {"$group": {"_id": None, "count": {"$sum": 1}}},
                ]
            )
            # update the dictionary with the updated count

        else:
            total = completed.aggregate(
                [
                    {
                        "$match": {
                            "user_email": user_email,
                            "oName": re.compile(
                                r"\\|" + re.escape(f"{xp_name}") + "\\|"
                            ),
                        }
                    },
                    {"$group": {"_id": None, "count": {"$sum": 1}}},
                ]
            )
        # update the dictionary with the updated count if it exists
        query_return = list(total)
        logger.info(f"DB returns for {xp_name}: " + str(query_return))
        if query_return:
            xp_dict[xp_name] = query_return[0].get("count")
        else:
            xp_dict[xp_name] = 0
        logger.info(f"xp_dict so far: {xp_dict}")

    logger.info(f"Completed Tasks for {user_email}: {xp_dict}")

    # And finally render the dashboard template

    return render_template(
        "user_dash_new.html",
        user_email=user_email,
        active_xps=active_xps,
        all_xps=all_xps,
        xp_info=xp_info,
        error=error,
        launch_xp=launch_xp,
        completed_tasks=xp_dict,
        max_tasks=max_tasks,
    )
