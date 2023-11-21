from slack_bolt import App
from slack_sdk import WebClient
from slack_bolt.adapter.socket_mode import SocketModeHandler

import argparse, json
import os, sys

import evadb, openai

import requests
from requests_html import HTMLSession
from bs4 import BeautifulSoup

# Connect to EvaDB and get a database cursor
cursor = evadb.connect().cursor()
cursor.query("""
    CREATE DATABASE IF NOT EXISTS data WITH ENGINE = 'hackernews', PARAMETERS = {
     "maxitem": "100"
    };
""").df()

# Stablish an HTML agent
session = HTMLSession()

# Create a function for the text summarizer
cursor.query("""
    CREATE FUNCTION IF NOT EXISTS TextSummarizer
    TYPE HuggingFace
    TASK 'summarization'
    MODEL 'facebook/bart-large-cnn'
""").df()

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
        sys.exit()
    except json.JSONDecodeError:
        print(f"Error parsing JSON in '{file_path}'.")
        sys.exit()

# Fetch data from a URL and return it as a JSON object
def fetch_json_data(url):
    response = session.get(url)
    if response.status_code == 200:
        data = json.loads(response.text)
        return data
    else:
        return None

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

def ask_gpt(text_query):
    return  openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": f"{text_query}"}]
                ).choices[0].message.content

# Initialize the bot
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

# Respond to any messages
@app.message(".*")
def message_hello(message, say):
    evaql_syntax = """
        SELECT
        FROM
        WHERE
        ORDER BY
        JOIN LATERAL
        SEGMENT()
        AS
        TextSummarizer(text) (Has to always be excuted for one item using LIMIT, also it can't be used with the keyword AS)
        (You cannot use other functions outside of the defined previously (eg. LOWER()))
    """
    sql_query = ask_gpt(f"""
            Create a query responding to the users request: {message["text"]}
            The definition of the different tables is:
        
            data.items: id, deleted, type, by, time, text, dead, parent, poll, kids, url, score, title, parts, descendants

            data.users: id, created, karma, about, submitted

            data.top_stories: id

            data.new_stories: id

            data.best_stories: id 

            data.ask_stories: id 

            data.show_stories: id 

            data.job_stories: id 

            data.updates: items, profiles 

            The syntax you can use only contains:
            {evaql_syntax}
            Do not use WHERE id = x unles the id is specifiyed explicitly by the user.
            Answer only the query in plain text, nothing else.
            If you can't create a query, just respond NONE
        """)
        
    # Execute the query
    try:
        if (sql_query != "NONE"):
            result = cursor.query(sql_query).df()
            number_entries = 0
            # Print the query
            for index, row in result.iterrows():
                text_row = ""
                for col in result.columns:
                    text_row += f"*{col[col.find('.')+1:].capitalize().replace('_', ' ')}*: {row[col]} "
                say(text_row)
                number_entries += 1
            
            say(f"Number of results: {number_entries}") 
        else:
            say(f""" Sorry, I could not convert your request to a SQL query :(""")
    except Exception as e:
        say(f""" Sorry, I could not convert your request to a SQL query :( \nError: {str(e)}""")
    say(f"Related Query: {sql_query}")

if __name__ == "__main__":

    # Inialize the app
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

    # Run the bot
    app.run(debug=True)

