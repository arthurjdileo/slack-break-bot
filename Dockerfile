FROM python:3
ADD bot.py /

RUN pip install flask
RUN pip install slackclient==2.0.0
RUN pip install datetime
RUN pip install apscheduler
RUN pip install pytz

CMD ["python3", "bot.py"]
