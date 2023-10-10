#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Simple Bot to reply to Telegram messages.

This file contains code for a simple Telegram bot that can reply to messages.
It defines a few command handlers for the /start and /help commands, as well
as a message handler for non-command messages. The bot runs until the user
presses Ctrl-C on the command line.

Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

# Import necessary modules
import logging
import os
from dotenv import load_dotenv
from telegram import *
from telegram import __version__ as TG_VER
import requests
import json

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from plankton.database import Database


# Define the path to the .env file
dotenv_path = os.path.join(".env")

# Load the .env file
load_dotenv(dotenv_path)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hello this is a simple chatbot that is trained on the MOF website. Arabic works but is not optimized",
        reply_markup=ForceReply(selective=True),
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Echo the user message by sending it to the MOF website chatbot API and returning the response.

    Args:
    - update (telegram.Update): The update object representing the incoming message.
    - context (telegram.ext.CallbackContext): The context object for the current update.

    Returns:
    - None
    """
    message: str = update.message.text

    # Inform user that bot is processing the message
    await update.message.reply_text(
        "Please give us a moment while we lookup your request..."
    )

    # Send the user message to the MOF website chatbot API
    response = requests.post(
        "http://backend:9091/ask",
        json={"question": message},
        headers={"X-API-KEY": os.getenv("API_SECRET_TOKEN")},
        timeout=300,
    )

    # Get the response from the MOF website chatbot API

    try:
        answer = json.loads(response.text)
        # get only the answer from the response
        answer = answer["output"]
    except:
        answer = response

    logger.info(f"asked: {message}")
    logger.info(f"answer: {answer}")

    # Send the response from the MOF website chatbot API back to the user
    await update.message.reply_text(f"{answer}")


def main() -> None:
    """
    Start the bot.

    Args:
    - None

    Returns:
    - None
    """
    # Create the Application and pass it your bot's token.
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError(
            "Telegram token not found in environment variable TELEGRAM_TOKEN"
        )
    application = Application.builder().token(token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
