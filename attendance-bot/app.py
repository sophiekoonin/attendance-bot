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
HELP_TEXT = ("I am the attendance bot! :robot_face::memo:\n"
             "Type `/attendance` followed by `here` or `absent`, the date as DD/MM/YY, and the name, e.g.:\n"
             "`/attendance here 02/10/17 Beyonce Knowles` \n"
             "`/attendance absent 02/01/17 Chaka Khan`")
BAD_COMMAND = ("Sorry, I didn't understand that command. :disappointed:"
               "\nType `/attendance help` for instructions.")
BAD_DATE = ("Sorry, that date doesn't seem to match up with any of our rehearsals. :confused:\n"
            "Please make sure you write it in the format DD/MM/YY and that it's a Monday!\n"
            "Type `/attendance help` for more info.")
BAD_NAME = "Sorry, I couldn't find anyone with that name. :confused:"
THANKS = "Thanks! I have updated attendance for {real_name} on {date}. :thumbsup:"
ATTENDANCE_MSG = (":dancing_banana: Rehearsal day! :dancing_banana: <!channel> Please indicate whether"
                     " or not you can attend tonight by reacting to this message with :thumbsup: (present) or "
                     ":thumbsdown: (absent).\nTo volunteer for Physical warm wp, respond with :muscle:. For Musical warm up, respond with :musical_note:.")

@app.route('/')
def hello_world():
    return 'Hello World! Attendance bot is running and ready.'


app.add_url_rule('/attendance', view_func=slack.dispatch)


@slack.command('attendance', token=SLASH_TOKEN,
               team_id=TEAM_ID, methods=['POST'])
def attendance(**kwargs):
    input_text = kwargs.get('text')
    user_id = kwargs.get('user_id')
    if len(input_text) == 0 or 'help' in input_text:
        return slack.response(HELP_TEXT)
    elif 'report' in input_text:
        return slack.response(bot.create_absence_message())
    elif 'updatemembers' in input_text:
        return slack.response(check_admin(user_id, trigger_update))
    elif 'post' in input_text:
        return slack.response(check_admin(user_id,post_attendance_message))
    elif 'process' in input_text:
        return slack.response(check_admin(user_id,process_all))
    elif 'here' in input_text:
        return slack.response(process_single_attendance(input_text, bot.record_presence))
    elif 'absent' in input_text:
        return slack.response(process_single_attendance(input_text, bot.record_absence))
    elif 'ignore' in input_text:
        return slack.response(check_admin(user_id, set_ignore, input_text))
    else:
        return slack.response(BAD_COMMAND)

def post_attendance_message():
    bot.post_message_with_reactions(ATTENDANCE_MSG)
    return "OK, posting a message now."

def process_all():
    return bot.process_attendance()

def check_admin(user_id, func, *args):
    if bot.is_admin(user_id):
        return func(*args)
    return ":no_entry: Sorry, you don't have permission to do that. :closed_lock_with_key:"

def trigger_update():
    bot.update_members()
    return "Member database has been updated. :thumbsup:"


def set_ignore(input_text):
    input_list = input_text.strip().split(' ')
    if 'stop' in input_text:
        flag = False
        real_name = ' '.join(input_list[2:]).strip()
    else:
        flag = True
        real_name = ' '.join(input_list[1:]).strip()
    slack_id = bot.get_slack_id(real_name)
    if slack_id is None:
        return "Please check the name and try again."
    bot.set_ignore(slack_id, flag)
    return "{} has been set to ignore = {}.".format(real_name, flag)


def process_single_attendance(input_text, attendance_func):
    msg = "You typed: `{}`\n".format(input_text)
    input_list = input_text.strip().split(' ')
    date = input_list[1]
    real_name = ' '.join(input_list[2:]).strip()
    ts = bot.get_timestamp(date)
    if ts is None:
        return msg + BAD_DATE
    slack_id = bot.get_slack_id(real_name)
    if not slack_id:
        return msg + BAD_NAME
    attendance_func(slack_id, ts)
    return msg + THANKS.format(real_name=real_name, date=date)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
