from slackbot.bot import Bot, respond_to, listen_to
import os
import evadb

# Configure your bot's API token
API_TOKEN = "YOUR_SLACK_API_TOKEN"
os.environ["OPENAI_KEY"] = "sk-..."

# Initialize the bot
bot = Bot()
# Connect to EvaDB and get a database cursor
cursor = evadb.connect().cursor()

@listen_to('.*')  # Matches any message
def handle_message(message):
    pass



if __name__ == "__main__":
    bot.run()