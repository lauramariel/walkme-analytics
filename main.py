from flask import Flask, request
from config import logger
from user_lookup import lookup_user_by_id
from threading import Thread
import config
import datetime
import mysql.connector

app = Flask(__name__)

env = config.ENV
required = config.REQUIRED_VALUES
db_connect_str = (
    "host='db_host', user='root', database='walkme_analytics', connect_timeout=10,"
)

# connect to DB
try:
    db = mysql.connector.connect(db_connect_str)
    cursor = db.cursor()
except mysql.connector.Error as err:
    logger.error(format(err))


class Process(Thread):
    def __init__(self, request, kind):
        Thread.__init__(self)
        self.request = request
        self.kind = kind

    def run(self):
        # get the payload
        payload = self.request.get_json()

        # save the values we care about
        item_id = payload["oId"]
        item_name = payload["oName"]
        created_at = datetime.datetime.fromtimestamp(
            payload["created_at"] / 1000
        ).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{created_at}")
        user_id = payload["wm.euId"]
        browser_name = payload["env.browser.name"]
        browser_ver = payload["env.browser.version"]
        os_name = payload["env.os.name"]
        walkme_env = payload["wm.env"]
        url = payload["ctx.location.hostname"]
        title = payload["ctx.title"]
        if "wm.language" in payload:
            language = payload["wm.language"]
        else:
            language = ""

        # convert user_id to email
        user_email = lookup_user_by_id(env, user_id)
        logger.info(f"User email: {user_email}")

        # if it's a task, store it in task table
        # with proper names
        if self.kind == "task":
            table_name = config.TABLE_NAMES["tasks"]
            id_col = "task_id"
            name_col = "task_name"

        # if it's a SWT started event, store it in the started table
        elif self.kind == "started":
            table_name = config.TABLE_NAMES["started"]
            id_col = "swt_id"
            name_col = "swt_name"

        # Insert into DB
        add_data = (
            f"INSERT INTO {table_name} "
            f"(created_at, user_id, user_email, {id_col}, {name_col},"
            " browser_name, browser_ver, os_name, walkme_env, url,"
            " title, language) "
            f"VALUES('{created_at}', '{user_id}', '{user_email}',"
            f"{item_id}, '{item_name}', '{browser_name}', "
            f"'{browser_ver}', '{os_name}', {walkme_env}, '{url}', "
            f"'{title}', '{language}')"
        )
        try:
            cursor.execute(add_data)
            db.commit()
            logger.info("Successfully inserted data into DB")
        except mysql.connector.Error as err:
            logger.error(format(err))
        cursor.close()
        db.close()
        logger.debug("Done Processing")


@app.route("/analytics/api/v1/walkmetasks", methods=["POST"])
def process_task_webhook():
    # if Content-Type=application/json
    logger.info("Ready")
    if request.is_json:
        payload = request.get_json()

        if not all(k in payload for k in required):
            logger.error("Missing expected values")
            logger.error(payload)
            return ("Missing expected values", 400)

        logger.debug(payload)
        logger.debug("Processing Request")

        thread = Process(request.__copy__(), "task")
        thread.start()

        return ("Accepted", 200)
    else:
        logger.error("Request is not json")
        return ("Invalid request", 400)


@app.route("/analytics/api/v1/walkmestarted", methods=["POST"])
def process_swt_started_webhook():
    # if Content-Type=application/json
    if request.is_json:
        payload = request.get_json()

        if not all(k in payload for k in required):
            logger.error("Missing expected values")
            logger.error(payload)
            return ("Missing expected values", 400)

        logger.debug(payload)
        logger.info("Processing Request")

        thread = Process(request.__copy__(), "started")
        thread.start()

        return ("Accepted", 200)
    else:
        logger.error("Request is not json")
        return ("Invalid request", 400)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
