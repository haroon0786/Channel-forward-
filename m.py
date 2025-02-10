import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Configure logging to see debug output in the console.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # You can change this to DEBUG for even more details.
)

class MediaGroupForwarder:
    def __init__(self, sources, destinations, delay=2.5):
        """
        :param sources: List of source channel IDs.
        :param destinations: List of destination channel IDs.
        :param delay: Delay in seconds to allow media groups to gather all messages.
        """
        self.sources = sources
        self.destinations = destinations
        self.media_groups = {}
        self.lock = asyncio.Lock()
        self.delay = delay

    async def handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Log the entire update for debugging purposes.
        logging.debug(f"Received update: {update}")

        # Process only channel posts.
        if not update.channel_post:
            logging.debug("Update is not a channel post. Ignoring.")
            return

        chat_id = update.channel_post.chat.id
        if chat_id not in self.sources:
            logging.debug(f"Channel {chat_id} is not in the source list. Ignoring.")
            return

        source_id = chat_id
        msg = update.channel_post
        media_group_id = msg.media_group_id

        if media_group_id:
            # Use a tuple (source_id, media_group_id) as the key.
            key = (source_id, media_group_id)
            async with self.lock:
                if key not in self.media_groups:
                    self.media_groups[key] = {'messages': [], 'task': None}
                    self.media_groups[key]['task'] = asyncio.create_task(
                        self.process_group(key, context, source_id)
                    )
                self.media_groups[key]['messages'].append(msg)
                logging.info(f"Added message {msg.message_id} to media group {media_group_id} from source {source_id}")
        else:
            await self.forward_single(msg, context, source_id)

    async def process_group(self, key, context: ContextTypes.DEFAULT_TYPE, source_id: int):
        # Wait to allow all media group messages to arrive.
        await asyncio.sleep(self.delay)
        async with self.lock:
            if key not in self.media_groups:
                return

            messages = sorted(self.media_groups[key]['messages'], key=lambda x: x.message_id)
            message_ids = [m.message_id for m in messages]
            media_group_id = key[1]

            for dest_id in self.destinations:
                try:
                    await context.bot.forward_messages(
                        chat_id=dest_id,
                        from_chat_id=source_id,
                        message_ids=message_ids
                    )
                    logging.info(
                        f"Forwarded media group {media_group_id} (messages: {message_ids}) "
                        f"from source {source_id} to destination {dest_id}"
                    )
                except Exception as e:
                    logging.error(f"Error forwarding media group {media_group_id} to destination {dest_id}: {e}")

            # Remove the media group data after processing.
            del self.media_groups[key]

    async def forward_single(self, message, context: ContextTypes.DEFAULT_TYPE, source_id: int):
        for dest_id in self.destinations:
            try:
                await context.bot.forward_message(
                    chat_id=dest_id,
                    from_chat_id=source_id,
                    message_id=message.message_id
                )
                logging.info(
                    f"Forwarded single message {message.message_id} from source {source_id} to destination {dest_id}"
                )
            except Exception as e:
                logging.error(f"Error forwarding message {message.message_id} to destination {dest_id}: {e}")

if __name__ == '__main__':
    # Define multiple source channel IDs (ensure the bot is added to these channels with proper permissions).
    sources = [
        -1002168050616,  # First source channel ID
        -1002168050616   # Second source channel ID
    ]
    # Define multiple destination channel IDs (ensure the bot has rights to post in these channels).
    destinations = [
        -1002382776169,
        -1002343397921,
        -1002229641386,
        -1002196447762,
        -1002167030823,
        -1002162952166,
        -1002229641386,
        -1002217505665,
        -1002244860035,
        -1002211149019,
        -1002213281912,
        -1002207249137
    ]

    forwarder = MediaGroupForwarder(sources, destinations)
    
    application = ApplicationBuilder().token('7893173971:AAH7v3zT8KKX3gCtDdIrkL9PsffZodPiTSM').build()

    # The MessageHandler with filters.ALL will capture all types of updates.
    application.add_handler(MessageHandler(filters.ALL, forwarder.handle_update))

    # Optionally, specify allowed_updates if you need to ensure channel posts are received:
    # allowed_updates = ["channel_post", "message", "edited_channel_post"]
    # application.run_polling(allowed_updates=allowed_updates)

    # Otherwise, run polling normally:
    application.run_polling()
