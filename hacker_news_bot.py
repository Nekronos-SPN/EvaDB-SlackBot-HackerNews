from slack_bolt import App
from slack_sdk import WebClient
from slack_bolt.adapter.socket_mode import SocketModeHandler

import argparse, json
import os, sys

import evadb, openai
# Connect to EvaDB and get a database cursor
cursor = evadb.connect().cursor()

JSON_FILE_PATH = None

# Load API KEYS from json file
# Format = { "API" = "KEY", ... }
def load_api_keys_from_json(file_path):
    try:
        with open(file_path, 'r') as json_file:
            api_keys = json.load(json_file)
            for key, value in api_keys.items():
                os.environ[key] = value
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        sys.exit();
    except json.JSONDecodeError:
        print(f"Error parsing JSON in '{file_path}'.")
        sys.exit();

def parse_arguments():
    # JSON for API Keys 
    global JSON_FILE_PATH
    parser = argparse.ArgumentParser(description="Load API keys from a JSON file and set them as environment variables.")
    parser.add_argument("-i", "--input", help="Path to the JSON file containing API keys", required=True)

    args = parser.parse_args()
    JSON_FILE_PATH = args.input


# Get the API tokens for config
parse_arguments()
load_api_keys_from_json(JSON_FILE_PATH)

openai.api_key = os.environ.get("OPENAI_API_KEY")

# Initialize the bot
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

# Respond to any messages
@app.message(".*")
def message_hello(message, say):
    text = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": f"""
            {message["text"]} (Answer as a chatbot dedicated to help user browse the HackerNews Webpage. The user can interact with you reacting to the message you are about to respond, the possible reactions are:
            1️⃣ : Top stories
            2️⃣:: New stories
            3️⃣:: Best stories
            4️⃣:: Latest asks
            5️⃣:: Latest shows
            6️⃣:: Latest jobs
            Please, state explicitly that they have to react to the message you sent)"""}]
            ).choices[0].message.content
    say(text)
    

@app.event("reaction_added")
def handle_reaction_added(event, say):

    item = event["item"]

    # Get the most recent message
    channel_id = item["channel"]
    response = client.conversations_history(channel=channel_id)
    last_message = response["messages"][0]

    # Check timestamp
    message_ts = item["ts"]
    last_message_ts = last_message["ts"]
    # Only answer to reactions to the last message
    if last_message_ts != message_ts:
        return

    action_mapping = {
        "one": "Search top stories",
        "two": "Search new stories",
        "three": "Search best stories",
        "four": "Search latest ask",
        "five": "Search latest show",
        "six": "Search latest job",
    }

    say(action_mapping[event["reaction"]])

if __name__ == "__main__":

    # Inialize the app
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

    # Run the bot
    app.run(debug=True)

