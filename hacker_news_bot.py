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
    CREATE DATABASE IF NOT EXISTS sqlite_data WITH ENGINE = 'sqlite', PARAMETERS = {
     "database": ":memory:"
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
    response = requests.get(url)
    if response.status_code == 200:
        data = json.loads(response.text)
        return data
    else:
        return None


# Fetch and populate database
def populate_table(url):
    # Drop the existing table if it exists
    cursor.query("DROP TABLE IF EXISTS hacker_news_data").df()

    # Create a table for storing Hacker News data
    cursor.query("""
        CREATE TABLE hacker_news_data (
            id INTEGER UNIQUE,
            deleted INTEGER,
            type TEXT(7),
            by TEXT(255),
            time INTEGER,
            text TEXT(ANYDIM),
            dead INTEGER,
            parent INTEGER,
            poll INTEGER,
            kids NDARRAY INT32(ANYDIM),
            url TEXT(255),
            score INTEGER,
            title TEXT(255),
            parts NDARRAY INT32(ANYDIM),
            descendants INTEGER,
            content TEXT(ANYDIM)
        )
    """).df()

    data = fetch_json_data(url)
    if data:
        # Data limiter
        LIMIT = 10
        for item_id in data:
            item_details = fetch_json_data(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json?print=pretty")
            if item_details:
                # Process the data and insert it
                cursor.query(f'''
                    INSERT INTO hacker_news_data (
                        id, deleted, type, by, time, text, dead, parent, poll, kids, url, score, title, parts, descendants, content
                    ) VALUES (
                        {item_id},
                        {1 if item_details.get('deleted', False) else 0},
                        "{item_details.get('type', 'NA').replace('"', "'").replace(";", "")}",
                        "{item_details.get('by', 'NA').replace('"', "'").replace(";", "")}",
                        {item_details.get('time', 0)},
                        "{BeautifulSoup(item_details.get('text', 'Empty Text'), "html.parser").text.replace('"', "'").replace(";", "")}",
                        {1 if item_details.get('dead', False) else 0},
                        {item_details.get('parent', 0)},
                        {item_details.get('poll', 0)},
                        {json.dumps(item_details.get('kids', []))},
                        "{item_details.get('url', 'NA').replace('"', "'").replace(";", "")}",
                        {item_details.get('score', 0)},
                        "{item_details.get('title', 'Empty Text').replace('"', "'").replace(";", "")}",
                        {json.dumps(item_details.get('parts', []))},
                        {item_details.get('descendants', 0)},
                        "{" ".join(BeautifulSoup(session.get(item_details.get('url')).text, "html.parser").text.replace('"', "'").replace(";", "").split()) if item_details.get('url') != None else 'Empty Text'}")
                '''
                ).df()
                if LIMIT == 0:
                    break
                LIMIT -= 1


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

# Createa a query to the database
def create_sql_query(message, say):
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
    sql_query = ask_gpt(f"""Using this table schema:
            CREATE TABLE hacker_news_data (
                id INTEGER UNIQUE,
                deleted INTEGER,
                type TEXT(7),
                by TEXT(255),
                time INTEGER,
                text TEXT(ANYDIM),
                dead INTEGER,
                parent INTEGER,
                poll INTEGER,
                kids NDARRAY INT32(ANYDIM),
                url TEXT(255),
                score INTEGER,
                title TEXT(255),
                parts NDARRAY INT32(ANYDIM),
                descendants INTEGER,
                content TEXT(ANYDIM)
            )
            The syntax you can use only contains:
            {evaql_syntax}
            Create a query responding to the users request: {message["text"]}
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


            

# Initialize the bot
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

ongoing_query = False

# Respond to any messages
@app.message(".*")
def message_hello(message, say):
    global ongoing_query

    # Check if the user asks for a SQL query
    if(ongoing_query and message["text"] == "NEW"):
        ongoing_query = False
    
    # If there is an ongoing query, create a sql statement
    if (ongoing_query):
        create_sql_query(message, say);
    else:
        text = ask_gpt(f"""
            {message["text"]} (Answer as a chatbot dedicated to help user browse the HackerNews Webpage. The user can interact with you reacting to the message you are about to respond, the possible reactions are:
            1️⃣: Tp stories
            2️⃣:New stories
            3️⃣:Best stories
            4️⃣:Latest asks
            5️⃣:Latest shows
            6️⃣:Latest jobs
            Please, state explicitly that they have to react to the message you sent)
        """)

        # Tell the user to choose an option
        say(text)
    

@app.event("reaction_added")
def handle_reaction_added(event, say):
    global ongoing_query

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

    reaction_mapping = {
        "one": "top stories",
        "two": "new stories",
        "three": "best stories",
        "four": "latest ask",
        "five": "latest show",
        "six": "latest job"
    }
    text = f"""
        The user chose {reaction_mapping[event["reaction"]]}.
        Tell them that its going to take a while to load the data and provide them with a random fun fact (please be original) in a separate paragraph.
        """
    # Make the mean time more amussing
    say(ask_gpt(text))

    url_mapping = {
        "one": "https://hacker-news.firebaseio.com/v0/topstories.json?print=pretty",
        "two": "https://hacker-news.firebaseio.com/v0/newstories.json?print=pretty",
        "three": "https://hacker-news.firebaseio.com/v0/beststories.json?print=pretty",
        "four": "https://hacker-news.firebaseio.com/v0/askstories.json?print=pretty",
        "five": "https://hacker-news.firebaseio.com/v0/showstories.json?print=pretty",
        "six": "https://hacker-news.firebaseio.com/v0/jobstories.json?print=pretty"
    }
    # Insert all values from HN into database
    url = url_mapping[event["reaction"]]
    if (url):
        ongoing_query = True
        populate_table(url)
        say(ask_gpt("Briefly tell the user that the data is ready, you will only show 5 entries from the hundreds you have"))
        preview = cursor.query("SELECT title, url FROM hacker_news_data LIMIT 5").df()
        for index, row in preview.iterrows():
            say(f"{row['hacker_news_data.title']}: {row['hacker_news_data.url']}")
        say(ask_gpt("Let the user know that he can manipulate all the data, he just needs to tell you what he wants to do"))
        say("Please type NEW to reset data")


if __name__ == "__main__":

    # Inialize the app
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()

    # Run the bot
    app.run(debug=True)

