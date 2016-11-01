from flask import Flask
from settings import config
from flask_slack import Slack
from bot import AttendanceBot
import os

app = Flask(__name__)
slack = Slack(app)
bot = AttendanceBot(config)
SLASH_TOKEN = os.environ.get("SLASH_TOKEN")
TEAM_ID = os.environ.get("SLACK_TEAM_ID")
HELP_TEXT = ("I am the attendance bot! :robot::memo:"
             "Type `/attendance` followed by `here` or `absent`, the date as DD/MM/YY, and the name, e.g.:\n"
             "`/attendance here 02/10/17 Beyonce Knowles` \n"
             "`/attendance absent 02/01/17 Chaka Khan`")
BAD_COMMAND = ("Sorry, I didn't understand that command. :disappointed"
               "\nType `/attendance help` for instructions.")
BAD_DATE = ("Sorry, that date doesn't seem to match up with any of our rehearsals. :confused:\n"
            "Please make sure you write it in the format DD/MM/YY and that it's a Monday!"
            "Type `/attendance help` for more info.")
BAD_NAME = "Sorry, I couldn't find anyone with that name. :confused:"
THANKS = "Thanks! I have updated attendance for {real_name} on {date}. :thumbsup:"

@app.route('/')
def hello_world():
    return 'Hello World! Attendance bot is running and ready.'

app.add_url_rule('/attendance', view_func=slack.dispatch)


@slack.command('attendance', token=SLASH_TOKEN,
               team_id=TEAM_ID, methods=['POST'])
def attendance(**kwargs):
    input_text = kwargs.get('text')
    if len(input_text) == 0 or 'help' in input_text:
        return slack.response(HELP_TEXT)
    elif 'report' in input_text:
        return slack.response(bot.create_absence_message())
    elif 'here' in input_text:
        return process_attendance(input_text, bot.record_presence)
    elif 'absent' in input_text:
        return process_attendance(input_text, bot.record_absence)
    else:
        return slack.response(BAD_COMMAND)

def process_attendance(input_text, attendance_func):
    if len(input_text) == 0 or 'help' in input_text:
        return slack.response(HELP_TEXT)
    input_list = input_text.strip().split(' ')
    date = input_list[1]
    real_name = input_list[2:]
    ts = bot.get_timestamp(date)
    if ts is None:
        return slack.response(BAD_DATE)
    slack_id = bot.get_slack_id(real_name)
    if not slack_id:
        return slack.response(BAD_NAME)
    attendance_func(slack_id, ts)
    return slack.response(
        THANKS.format(real_name=real_name, date=date))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
