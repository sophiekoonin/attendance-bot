from slackclient import SlackClient
import yaml

settings = yaml.load(open("settings.yaml"))

token = settings.get("bot-token")
bot_name = settings.get("bot-name")
bot_emoji = ":{emoji}:".format(emoji=settings.get("bot-emoji")) #wrap emoji name in colons

client = SlackClient(token)