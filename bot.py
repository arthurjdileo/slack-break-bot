'''
Title: TS Break Bot
Company: Teltech
Author: Arthur Dileo
www.arthurdileo.me
'''

from flask import *
from slackclient import SlackClient
import json
from datetime import datetime,timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import os
from google.cloud import datastore

app = Flask(__name__)

scheduler = BackgroundScheduler()
scheduler.start()

client = datastore.Client()
br = client.key("breaks", "breakData")

# notification increments in minutes
NOTIFICATIONS = [0, 15]
# Bot User OAuth Access Token
try:
    TOKEN = os.environ['SLACK_TOKEN']
except KeyError:
    print("Please add your Bot User OAuth Access Token as an environment variable.")
    exit()
# Channel ID
CHANNEL = "GE5QGDNRZ"

# health check
@app.route("/health", methods=['POST','GET'])
def health():
    return "ok"

@app.route("/break", methods=['POST', 'GET'])
def bot():
    if request.method == 'POST':
        # store requester and parameter
        user_id = request.form['user_id']
        param = request.form['text'].lower()
        now = datetime.now().strftime('%B %d, %Y')

        # starts the bot, wipes data file, wipes schedule
        # /break start
        if param == "start":
            return startBot()

        # sorts taken breaks and sends it to user
        # /break status
        if param == 'status':
            try:
                return statusBot()
            except:
                return helpCmd("_ERROR : Breaks have not started for the day._")

        # edits break of requester
        # /break change [time]
        elif "change" in param:
            param = param[7:]
            timeDate = configureTime(param) if configureTime(param) else -1
            if timeDate == -1:
                return helpCmd("_ERROR : You entered an invalid time._")
            if hasSelected(user_id) and not isTaken(param):
                return changeBot(user_id, param, now)
            elif not isTaken(param):
                return breakBot(user_id, param, timeDate, now)
            else:
                return helpCmd("_ERROR : This break has already been taken._")

        # swaps break of requester w/ param
        # /break swap [time]
        elif "swap" in param:
            param = param[5:]
            timeDate = configureTime(param) if configureTime(param) else -1
            if timeDate == -1:
                return helpCmd("_ERROR : You entered an invalid time._")
            try:
                new_id = getUserByTime(param)
                if new_id == user_id:
                    return helpCmd("_ERROR : You already have this break._")
            except:
                return changeBot(user_id, param, now)

            if hasSelected(user_id) and hasSelected(new_id):
                return swapBot(user_id, new_id, now)
            else:
                return helpCmd("_ERROR : <@" + user_id + "> did not yet select a break._")

        # remove break at time
        # /break remove [time]
        elif "remove" in param:
            param = param[7:]
            timeDate = configureTime(param) if configureTime(param) else -1
            if timeDate == -1:
                return helpCmd("_ERROR : You entered an invalid time._")
            try:
                key = getUserByTime(param)
            except:
                return helpCmd("_ERROR : This time is not taken._")
            return removeBot(key)

        # provides help text
        elif param == "help":
            return helpCmd()

        # stores break of requester
        else:
            timeDate = configureTime(param) if configureTime(param) else -1
            if timeDate == -1:
                return helpCmd("_ERROR : You entered an invalid time. E.g. 2:00pm_")
            elif not hasSelected(user_id) and not isTaken(param):
                return breakBot(user_id, param, timeDate, now)
            elif hasSelected(user_id) and not isTaken(param):
                return changeBot(user_id, param, now)
            else:
                return helpCmd("_ERROR : You either chose a break already or the break" \
                       " time is already taken._")


# sends a message to a user/channel
def sendMessage(dest, message):
    sc.api_call(
        "chat.postMessage",
        link_names=1,
        channel=dest,
        text=message
    )
    return

# writes to data file - overwrites any previous data
def writeJson(data):
    with open("breakdata.json", "w") as f:
        json.dump(data, f)

# loads json file
def loadData():
    with open('breakdata.json', "r") as f:
        return json.load(f)

# appends file with new data
def reloadJson(user_id, param):
    origData = loadData()
    origData[user_id] = param
    writeJson(origData)

# checks if user has already selected a break
def hasSelected(user_id):
    breaks = loadData()
    for key in breaks:
        if str(user_id).lower() == str(key).lower():
            return True
    return False

# checks if time is taken
def isTaken(time):
    time = time.lower()
    breaks = loadData()
    for key in breaks:
        if breaks[key].lower() == time:
            return True
    return False

# sorts times and returns a list
def sortTimes():
    breaks = loadData()
    return sorted(breaks.items(), key=lambda kv: kv[1])

# sends msg to user reminding them X minutes before break
def reminder(user_id, delta):
    if delta == 0:
        sendMessage(user_id, "Your break starts now!")
    else:
        sendMessage(user_id, "Your break starts in " + str(delta) + " minutes.")

# find user_id given the time
def getUserByTime(time):
    breaks = loadData()
    times = breaks.items()
    for t in times:
        if t[1] == time:
            return str(t[0])
    raise AssertionError("ERROR : Cannot find user.")

# format + validity check
# return -1 if invalid
def configureTime(param):
    try:
        selectedTime = datetime.time(datetime.strptime(param, "%I:%M%p"))
        now = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
        timeDate = datetime.combine(now, selectedTime)
        timeDate = pytz.timezone("US/Eastern").localize(timeDate)
    except:
        return -1
    return timeDate

# removes all scheduling jobs for a user
def removeJobs(user_id):
    jobIds = getJobIds(user_id)
    for j in jobIds:
        scheduler.remove_job(j)

# add reminder job based off notifications + time
def addJobs(user_id, notif, time=None, timeDate=None):
    if timeDate == None:
        timeDate = configureTime(time) if configureTime(time) else -1
    if timeDate == -1:
        return helpCmd("_ERROR : You entered an invalid time._")
    for delta in notif:
        scheduler.add_job(reminder, 'date',
                          run_date = timeDate-timedelta(minutes=delta) if delta!=0 else timeDate,
                      args=[user_id, delta], id=user_id + str(delta))

# gets job id's for a user
def getJobIds(user_id):
    jobs = scheduler.get_jobs()
    listOfJobs = list()
    for j in jobs:
        if j.id.__contains__(user_id):
            listOfJobs.append(j.id)
    return listOfJobs

# starts the bot, wipes data file, wipes schedule
def startBot():
    # create empty dict to store times
    writeJson({})
    scheduler.remove_all_jobs()
    scheduler.add_job(startBot, 'cron', day_of_week='mon,tue,wed,fri', week='*',
                      month='*', year='*', timezone="US/Eastern", hour=10)
    sendMessage(CHANNEL,
                "* @channel The BreakBot is now accepting breaks for the day.*")
    return ""

# returns current breaks
def statusBot():
    status = sortTimes()
    times = "Breaks for the day:\n"
    for br in status:
        times = \
            times + ("<@" + br[0] + "> is taking a break at " + br[1] + "\n")
    return times

# swaps break of requester w/ param
def swapBot(orig_id, new_id, now):
    breaks = loadData()
    removeJobs(orig_id), removeJobs(new_id)
    newTime, oldTime = breaks[new_id], breaks[orig_id]
    breaks[new_id], breaks[orig_id] = breaks.pop(orig_id), newTime

    sendMessage(CHANNEL,
                "<@" + orig_id + "> has swapped their " + oldTime +
                " with <@" + new_id + ">'s break at " + breaks[orig_id])
    writeJson(breaks)
    breaks = loadData()
    addJobs(orig_id, NOTIFICATIONS, time=breaks[orig_id])
    addJobs(new_id,NOTIFICATIONS,time=breaks[new_id])
    sendMessage(orig_id,"Your break on *" + now +
                "* is scheduled for *" + breaks[orig_id] + "*.")
    sendMessage(new_id, "Your break on *" + now +
                "* is scheduled for *" + breaks[new_id] + "*.")
    return ""

# edits break of requester w/ new time
def changeBot(user_id, newTime, now):
    breaks = loadData()
    oldTime = breaks[user_id]
    del breaks[user_id]
    sendMessage(CHANNEL,
                "<@" + user_id + "> has changed their break from "
                + oldTime + " to " + newTime + ".")
    reloadJson(user_id, newTime)
    removeJobs(user_id)
    addJobs(user_id, NOTIFICATIONS, time=newTime)
    sendMessage(user_id, "Your break on *" + now +
                "* is scheduled for *" + newTime + "*.")
    return ""

# initiates the break
def breakBot(user_id, param, timeDate, now):
    reloadJson(user_id, param)
    addJobs(user_id, NOTIFICATIONS, timeDate=timeDate)
    sendMessage(CHANNEL, "<@" + user_id + "> is now taking a break at "
                + param + ". Use /break status to view all breaks.")
    sendMessage(user_id,"Your break on *" + now + "* is scheduled for *"
                + param + "*.")
    return ""

# provides available cmd's
def helpCmd(error=None):
    commands = '''
-------------------------
*Available Commands:*\n
/break [time] - reserves a break at [time].\n
/break status - view current breaks for the day.\n
/break remove [time] - removes a break at [time].\n
/break change [time] - changes break from current to [time].\n
/break swap [time] - swaps your time with someone's [time].\n
-------------------------
'''
    helpcmd = "*Use /break help for more assistance*"

    return (error + "\n\n" + helpcmd) if error != None else commands

# removes break of user
def removeBot(user_id):
    breaks = loadData()
    time = breaks[user_id]
    del breaks[user_id]
    writeJson(breaks)
    sendMessage(CHANNEL, "<@" + user_id + ">'s break at " + time +" has been removed.")
    removeJobs(user_id)
    return ""

sc = SlackClient(TOKEN)

# start bot on respective days at 10am
scheduler.add_job(startBot, 'cron', day_of_week='mon,tue,wed,fri', week='*',
                  month='*', year='*', timezone="US/Eastern", hour=10)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
