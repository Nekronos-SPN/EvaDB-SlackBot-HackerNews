from slack_bolt import App
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

# Initialize the bot
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Respond to any messages
@app.message(".*")
def message_hello(message, say):
    # Set OpenAI key.
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    say(
        openai.ChatCompletion.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": message["text"]}]
            )
        .choices[0]
        .message.content
        )

if __name__ == "__main__":

    # Inialize the app
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

    # Run the bot
    app.run(debug=True)

