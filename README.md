# Slack-Break-Bot
A slack bot to manage shift breaks for hourly employees.

## Getting Started
The following instructions will explain how to use the Slack bot.

### Installing Dependencies
Assure you have the following modules installed to assure a working slack bot:

```
Python 3.6
flask
slackclient 2.0
datetime
apscheduler
pytz
```

### Starting the bot

In the bot.py file, you can find the channel ID that it will post updates to as well as notification intervals that you can set. Also make sure to set your environment variable in the environment file with your Bot User OAuth Access Token. Then, to finish up, add a Slash Command in your Slack App page and set the request URL.

```
clear;python3 bot.py && . /environment
```

### Docker

I also included the Dockerfile setup so that if you want you can move it to a Kubernetes platform or similar. If you plan to just use docker, the JSON file is already mounted for you. However, if you move to a Kubernetes platform, you must ensure you account for persistance with the JSON file. I am planning to move to Google Datastore for v2.

```
clear;python3 run_docker.py
```
### Slack
Be sure to also set-up the app in the Slack API page (https://api.slack.com/apps) and setup the "slash commands" to use REST on this web server.
