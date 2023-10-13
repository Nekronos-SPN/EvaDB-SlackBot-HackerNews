# Slack-HackerNewsBot
Slack NewsBot is an intelligent chatbot designed to bring daily news updates directly to your Slack workspace. Powered by natural language processing and personalized interactions, this chatbot not only keeps your team informed but also engages in friendly conversations.

Usage: python hacker_news_bot.py -i api_keys.json 

Contents of api_keys.json:

{
        "SLACK_BOT_TOKEN": "xoxb-...",
        "SLACK_APP_TOKEN": "xapp-...,
        "OPENAI_API_KEY": "sk-..."
}

Python version: 3.11.5
Software stack:
	- ChatGPT for natural language processing
	- Slackbot for interacting with Slack API
	- EvaDB for the AI stack and relational storage
