from flask import Flask, request, Response, json
 
app = Flask(__name__)

@app.route("/")
@app.route("/index")
def index():
    return "<h1>Hello World!</h1>"

@app.route('/analytics/api/v1/walkmetasks', methods=['POST'])
def process_task_webhook():

    # task_id
    # friendly_name
    # user_id
    # user_email
    # date_completed
    # browser
    # environment

    # if Content-Type=application/json
    if request.is_json:
        payload = request.get_json()

        required = ['created_at', 'event_info']

        if not all (k in payload for k in required):
            return ("Missing values", 400)

        created_at = payload['created_at']
        event_info = payload['event_info']

        print("Payload received:")
        print(payload)
        print()

        print("created_at - " + str(type(created_at)))
        print(f"{created_at}")
        print("event_info - " + str(type(event_info)))
        print(f"{event_info}")
        print()

        return("Accepted", 200)
    else:
        print("ERROR: Request is not json")
        return("Invalid request", 400)

@app.route('/analytics/api/v1/walkmestarted', methods=['POST'])
def process_swt_started_webhook():
    # TBD
    return("OK", 200)

if __name__ == "__main__":
    app.run(host='0.0.0.0')