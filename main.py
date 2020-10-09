from flask import Flask, request
from config import logger

app = Flask(__name__)


@app.route("/")
@app.route("/index")
def index():
    return "<h1>Hello World!</h1>"


@app.route("/analytics/api/v1/walkmetasks", methods=["POST"])
def process_task_webhook():
    # if Content-Type=application/json
    if request.is_json:
        payload = request.get_json()

        required = [
            "oId",
            "oName",
            "env.browser.name",
            "env.browser.version",
            "env.os.name",
            "wm.euId",
            "wm.env",
            "created_at",
            "ctx.location.hostname",
        ]

        if not all(k in payload for k in required):
            logger.error("Missing expected values")
            logger.error(payload)
            return ("Missing expected values", 400)

        logger.info(payload)

        # task_id = payload["oId"]
        # task_name = payload["oName"]
        # browser_name = payload["env.browser.name"]
        # browser_ver = payload["env.browser.version"]
        # os_name = payload["env.os.name"]
        # user_id = payload["wm.euId"]
        # env = payload["wm.env"]
        # created_at = payload["created_at"]
        # url = payload["ctx.location.hostname"]

        return ("Accepted", 200)
    else:
        logger.error("Request is not json")
        return ("Invalid request", 400)


@app.route("/analytics/api/v1/walkmestarted", methods=["POST"])
def process_swt_started_webhook():
    # sample payload
    # {
    #    "sId": "1122a668-7f20-4ecf-83b3-45aa587fdff7",
    #    "oId": 744136,
    #    "oName": "Clusters Main Menu",
    #    "type": "play",
    #    "env.browser.name": "Chrome",
    #    "env.browser.version": "85.0.4183.83",
    #    "env.os.name": "MacOS",
    #    "wm.euId": "6ede1366dd24367bbd5dba50125e285f1e644d51d1a806cf958fbd6d",
    #    "wm.env": 0,
    #    "created_at": 1602211986142,
    #    "ctx.location.protocol": "https:",
    #    "ctx.location.hostname": "clustersptiknywzbx.nutanixtestdrive.com",
    #    "ctx.location.pathname": "/console/",
    #    "ctx.title": "Nutanix",
    #    "wm.userVars.name": "",
    #    "wm.userVars.role": "",
    #    "wm.userVars.type": "",
    #    "wm.userVars.status": "",
    #    "wm.userVars.info": "",
    #    "event_info": "<wm.euId> started Clusters Main Menu on Chrome
    #       85.0.4183.83 "
    # }

    return ("OK", 200)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
