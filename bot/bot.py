import logging
from telegram.ext import (
    Application,
    MessageHandler,
    filters
)
import httpx
import json
import asyncpg
import os

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")
NEUROCHAIN_API_KEY = os.getenv("NEUROCHAIN_API_KEY")
TELEGRAM_API_KEY = os.getenv("TELEGRAM_API_KEY")
async def store_in_db(message_text, sentiment, justification):
    conn = await asyncpg.connect(DATABASE_URL)

    # Create the table if it doesn't exist
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS sentiment_analysis (
            id SERIAL PRIMARY KEY,
            message TEXT,
            sentiment TEXT,
            justification TEXT
        )
    ''')

    # Insert the data into the table
    await conn.execute('''
        INSERT INTO sentiment_analysis(message, sentiment, justification) VALUES($1, $2, $3)
    ''', message_text, sentiment, justification)

    await conn.close()

# Function to handle incoming messages
async def handle_message(update, context):
    # Print the message to the console
    print(f"Message from {update.message.from_user.first_name}: {update.message.text}")
    url = 'https://ncmb.neurochain.io/tasks/message'
    data = {
        "model": "Mistral-7B-Instruct-v0.2-GPTQ",
        "prompt": f'[INST] You are sentiment analytic. respond in format SENTIMENT: sendiment, JUSTIFICATION: basis on which the sentiment was derived [/INST]provide sentiment of this message: {update.message.text}',
        "max_tokens": 1024,
        "temperature": 0.6,
        "top_p": 0.95,
        "frequency_penalty": 0,
        "presence_penalty": 1.1
    }
    # Headers (optional)
    headers = {
        'Content-Type': 'application/json',  # Specify content type if sending JSON data
        'Authorization': f'Bearer {NEUROCHAIN_API_KEY}'  # If authentication is required
    }
    # send post request to message broker to obtain message sentiment from group channel
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers, timeout=None)
        print(f'Status Code: {response.status_code}')
        print(f'Response Content: {response.text}')
        # store query data to the database
        parsed_response = json.loads(response)

        # Extract the 'text' field from the first item in the list
        text = parsed_response[0]['text']

        # Split the text to extract SENTIMENT and JUSTIFICATION
        sentiment = text.split("SENTIMENT: ")[1].split(", JUSTIFICATION: ")[0]
        justification = text.split(", JUSTIFICATION: ")[1]
        # Output the extracted information
        print(f"SENTIMENT: {sentiment}")
        print(f"JUSTIFICATION: {justification}")
        # Store the message, sentiment, and justification in the database
        await store_in_db(update.message.text, sentiment, justification)

def main():
    # Register a message handler to listen to all messages
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    """Run the bot."""
    # context_types = ContextTypes(context=CustomContext, chat_data=ChatData)
    application = Application.builder().token(TELEGRAM_API_KEY).concurrent_updates(True).build()
    # run track_users in its own group to not interfere with the user handlers
    application.add_handler(message_handler)
    application.run_polling()
    # Run the bot until it is stopped
    application.idle()


if __name__ == '__main__':
    main()