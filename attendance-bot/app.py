from flask import Flask
from flask_slack import Slack
from bot import AttendanceBot
import os
import yaml

app = Flask(__name__)
slack = Slack(app)
bot = AttendanceBot(yaml.load(open('../settings.yaml')))
SLASH_TOKEN = os.environ.get("SLASH_TOKEN")
TEAM_ID = os.environ.get("SLACK_TEAM_ID")
HELP_TEXT = ("I am the attendance bot! :robot::memo:"
             "Type /here or /absent followed by full name, date as DD/MM/YY, "
             "separated by a comma. e.g.:\n"
             "/here Beyoncé Knowles, 31/10/16\n"
             "/absent Chaka Khan, 02/01/17")

@app.route('/')
def hello_world():
    return 'Hello World! Attendance bot is running and ready.'


app.add_url_rule('/here', view_func=slack.dispatch)
app.add_url_rule('/absent', view_func=slack.dispatch)
app.add_url_rule('/attendance', view_func=slack.dispatch)

@slack.command('attendance', token=SLASH_TOKEN,
               team_id=TEAM_ID, methods=['POST'])
def get_attendance_details(**kwargs):
    input_text = kwargs.get('text')
    if len(input_text) == 0 or 'report' not in input_text:
        return slack.response(HELP_TEXT)
    return slack.response(bot.create_absence_message())

@slack.command('here', token=SLASH_TOKEN,
               team_id=TEAM_ID, methods=['POST'])
def member_present(**kwargs):
    input_text = kwargs.get('text')
    return process_attendance(input_text, bot.record_presence)


@slack.command('absent', token=SLASH_TOKEN,
               team_id=TEAM_ID, methods=['POST'])
def member_absent(**kwargs):
    input_text = kwargs.get('text')
    return process_attendance(input_text, bot.record_absence)


def process_attendance(input_text, attendance_func):
    if len(input_text) == 0 or 'help' in input_text:
        return slack.response(HELP_TEXT)
    input_list = input_text.strip().split(',')
    real_name = input_list[0].strip()
    date = input_list[1].strip()

    slack_id = bot.get_slack_id(real_name)
    if not slack_id:
        return slack.response("Sorry, I couldn't find anyone with that name. :confused:")
    attendance_func(slack_id, date)
    return slack.response(("Thanks! I have updated attendance for {real_name} on {date}. :thumbsup:").format(real_name=real_name, date=date))

if __name__ == '__main__':
    app.run()
