# Slack NewsBot - Intelligent Hacker News Chatbot

![Slack NewsBot](evadb-full-logo.svg)

**Slack NewsBot** is an intelligent chatbot designed to bring daily news updates directly to your Slack workspace. Powered by natural language processing and personalized interactions, this chatbot not only keeps your team informed but also engages in friendly conversations.

## Usage

To run the Slack NewsBot, use the following command:

```bash
python hacker_news_bot.py -i api_keys.json
Contents of api_keys.json:
```

Make sure you have a valid api_keys.json file with the following structure:
```json
{
        "SLACK_BOT_TOKEN": "xoxb-...",
        "SLACK_APP_TOKEN": "xapp-...,"
        "OPENAI_API_KEY": "sk-..."
}
```

## Software Stack
- Python version: 3.11.5
- Natural Language Processing: ChatGPT
- Database Content: Hacker News API
- Slack Integration: Slackbot
- AI Stack and Relational Storage: EvaDB
## Features

- Fetch and display Hacker News stories.
- Engage in interactive conversations with users.
- Execute SQL queries based on user requests.
- Provide data manipulation options to users.
- Easy integration with your Slack workspace.
  
## Getting Started
1. Clone the repository.
2. Install the required dependencies.
3. Set up a Slack App and obtain the necessary tokens.
4. Create an API key file (api_keys.json) with your tokens.
5. Run the bot using the provided command.

## Disclaimer
This project uses third-party APIs and tools, including the Hacker News API, Slack API, and OpenAI's GPT model. Make sure to comply with their terms of use and policies when using this bot.

Enjoy staying updated with the latest news with Slack NewsBot!
