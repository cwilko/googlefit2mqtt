from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import traceback
from datetime import datetime
import time
from dateutil import parser
import os
import sched
import paho.mqtt.client as mqtt

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')
TOKEN_URL = os.environ.get('TOKEN_URL')
MQTT_HOST = os.environ.get('MQTT_HOST')
MQTT_PORT = int(os.environ.get('MQTT_PORT'))
INTERVAL_HEART_RATE = int(os.environ.get('INTERVAL_HEART_RATE'))
INTERVAL_STEP_COUNT = int(os.environ.get('INTERVAL_STEP_COUNT'))

# The callback for when the client receives a CONNACK response from the server.


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))

client = mqtt.Client()
client.on_connect = on_connect

client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

s = sched.scheduler(time.time, time.sleep)

TODAY = datetime.today().date()
NOW = datetime.today()
ALT_DATE = parser.parse("2020-05-13")
START = int(time.mktime(TODAY.timetuple()) * 1000000000)
ALT_START = int(time.mktime(ALT_DATE.timetuple()) * 1000000000)
#START = ALT_START

if os.path.exists("data/timestamp"):
    try:
        f = open('data/timestamp', 'r')
        START = int(f.read())
        f.close()
    except Exception as e:
        print("Error reading timestamp")
        print(e)
        traceback.print_exc()

print("Starting from " + str(datetime.utcfromtimestamp(START // 1000000000)))

credentials = Credentials(None, refresh_token=REFRESH_TOKEN, token_uri=TOKEN_URL, client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
service = build('fitness', 'v1', credentials=credentials)


def get_heart_rate(sc, START):

    NOW = datetime.today()
    END = int(time.mktime(NOW.timetuple()) * 1000000000)
    #print("Until " + str(datetime.utcfromtimestamp(END // 1000000000)))
    DATA_SET = "%s-%s" % (START, END)

    try:

        response = service.users().dataSources().datasets().get(userId="me", dataSourceId="derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm", datasetId=DATA_SET).execute()

        for point in response["point"]:

            msg = str("health,type=heart_rate,app=googlefit bpm=%d %s" % (int(point["value"][0]["fpVal"]), point["startTimeNanos"]))
            #print(msg + " " + str(datetime.utcfromtimestamp(int(point["startTimeNanos"]) // 1000000000)))
            client.publish("telegraf/health/heart", msg)

        # Write out last timestamp
        if response["point"]:
            f = open('data/timestamp', 'w')
            f.write("%d" % (int(point["startTimeNanos"]) + 1))
            f.close()

            START = str(int(point["startTimeNanos"]) + 1)

    except Exception as e:
        print("Error during updating heart rate")
        print(e)
        traceback.print_exc()
    finally:
        s.enter(INTERVAL_HEART_RATE, 1, get_heart_rate, (sc, START,))


def get_step_count(sc):

    body = {
        "aggregateBy": [{
            "dataTypeName": "com.google.step_count.delta",
            "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
        }],
        "bucketByTime": {"durationMillis": 86400000},
        "startTimeMillis": int((time.mktime(TODAY.timetuple()) * 1000) - (30 * 86400000)),
        "endTimeMillis": int(time.mktime(TODAY.timetuple()) * 1000)
    }

    try:
        response = service.users().dataset().aggregate(userId="me", body=body).execute()

        for bucket in response["bucket"]:
            if (len(bucket["dataset"][0]["point"]) > 0):
                point = bucket["dataset"][0]["point"][0]
                #print(str(datetime.utcfromtimestamp(int(point["endTimeNanos"]) // 1000000000)))
                # print(point["value"][0]["intVal"])

                msg = str("health,type=step_count,app=googlefit steps=%d %s" % (int(point["value"][0]["intVal"]), point["endTimeNanos"]))
                #print(msg + " " + str(datetime.utcfromtimestamp(int(point["endTimeNanos"]) // 1000000000)))
                client.publish("telegraf/health/steps", msg)

    except Exception as e:
        print("Error during updating step count")
        print(e)
        traceback.print_exc()
    finally:
        s.enter(INTERVAL_STEP_COUNT, 1, get_step_count, (sc,))


# Kick off timers
s.enter(INTERVAL_HEART_RATE, 1, get_heart_rate, (s, START,))
s.enter(INTERVAL_STEP_COUNT, 1, get_step_count, (s,))
s.run()
