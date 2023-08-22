import asyncio
from datetime import datetime
import discord
import _secrets
import yaml
import os
import pytz

class DebugLogger:
    """
    A debug logger for a discord bot.

    This class logs messages and sends them to the bot developer, stored in _secrets.py.
    It saves the messages and flushes them every 10 seconds (or another interval, configurable via the SLEEP_TIME variable).
    If a message already exists, it edits that message to append new information.
    Messages are stored in a list, and the total character count is ensured to be under a limit (2000 by default, 
    configurable via the CHAR_LIMIT variable).
    If the total length of the messages exceeds the limit, the oldest message is discarded.
    The bot and current message information (including ID and content) are stored in a singleton instance of the class.

    Example usage:
    ```
    from debug_logger import DebugLogger
    debug_logger = DebugLogger.get_instance(bot) # Only need to pass the bot once
    debug_logger.start()
    debug_logger.log("Init complete")  # note the absence of "await" here
    ```
    """

    _instance = None
    bot = None
    DEBUG_INFO_FILE = 'data/debugconf.yaml'
    CHAR_LIMIT = 2000
    SLEEP_TIME = 10

    def __init__(self, bot=None):
        if bot is not None:
            DebugLogger.bot = bot
        if DebugLogger._instance is None:
            self.debug_message_list = []
            self.current_message_info = {'id': None, 'content': []}  # Initialize with no message ID and empty content
            DebugLogger._instance = self
        else:
            raise Exception("You cannot create another DebugLogger class!")  # Enforce singleton instance

    @classmethod
    def get_instance(cls, bot=None):
        # Get the singleton instance, or create it if it doesn't exist
        if cls._instance is None:
            cls(bot)
        return cls._instance

    def start(self):
        # Start the loop that sends log messages
        self.bot.loop.create_task(self.send_loop())

    def log(self, message):
        # Add a timestamp to the message and store it in the message list
        now = datetime.now(pytz.timezone('US/Central'))
        #timestamp = now.strftime("[%Y-%m-%d %H:%M:%S]")
        timestamp = now.strftime("%m-%d %H:%M:%S]")
        debug_message = f"{timestamp} {message}"
        self.debug_message_list.append(debug_message)
        print(debug_message)
        return debug_message

    async def get_developer(self):
        # Get the developer's discord user
        dev_id = _secrets.DEVELOPER_ID
        return self.bot.get_user(dev_id)

    def load_message_info(self):
        # Load the current message ID and content from the YAML file, or initialize them if the file doesn't exist
        if os.path.exists(self.DEBUG_INFO_FILE):
            with open(self.DEBUG_INFO_FILE, 'r') as f:
                self.current_message_info = yaml.safe_load(f)
        else:
            self.current_message_info = {'id': None, 'content': []}

    def save_message_info(self):
        # Save the current message ID and content to the YAML file
        with open(self.DEBUG_INFO_FILE, 'w') as f:
            yaml.safe_dump(self.current_message_info, f)

    async def flush(self):
        if self.debug_message_list:
            self.current_message_info['content'].extend(self.debug_message_list)
            self.debug_message_list = []

            lines = self.current_message_info['content']
            new_content = ""
            for line in reversed(lines):
                if len(new_content + line + "\n") <= self.CHAR_LIMIT:
                    new_content = line + "\n" + new_content
                else:
                    break
            new_content = new_content.strip()

            developer = await self.get_developer()

            self.load_message_info()

            if self.current_message_info['id']:
                try:
                    current_message = await developer.fetch_message(self.current_message_info['id'])
                    await current_message.edit(content=new_content)
                    self.current_message_info['content'] = new_content.split('\n')
                    self.save_message_info()
                except discord.NotFound:
                    current_message = await developer.send(content=new_content)
                    self.current_message_info = {'id': current_message.id, 'content': new_content.split('\n')}
                    self.save_message_info()
            else:
                current_message = await developer.send(content=new_content)
                self.current_message_info = {'id': current_message.id, 'content': new_content.split('\n')}
                self.save_message_info()

    async def send_loop(self):
        while True:
            await self.flush()  # Reuse the logic in the flush method
            await asyncio.sleep(self.SLEEP_TIME)