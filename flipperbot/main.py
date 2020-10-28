import mimetypes
import os
import sys
import urllib.request
from datetime import date

import discord
from dotenv import load_dotenv
from google.cloud import pubsub_v1, storage

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
CHANNEL = os.getenv('DISCORD_CHANNEL')

discord_client = discord.Client()
storage_client = storage.Client()
subscriber = pubsub_v1.SubscriberClient()


def _get_channel():
    guild = discord.utils.get(discord_client.guilds, name=GUILD)
    if not guild:
        return None

    channel = discord.utils.get(guild.channels, name=CHANNEL)
    return channel


def _handle_results(message):
    filename = message.data.decode('utf-8')
    print(f'Downloading {filename}')

    bucket = storage_client.get_bucket('war_rosters.msf.flipperkid.com')
    blob = bucket.get_blob(filename)
    text = blob.download_as_text()

    channel = _get_channel()
    if not channel:
        print(f'Unable to find channel {GUILD}#{CHANNEL}')

    discord_client.loop.create_task(channel.send(text))
    message.ack()


def _subscribe_to_results():
    topic_name = 'projects/flipperkid-default/topics/war_roster_results'
    subscription_name = 'projects/flipperkid-default/subscriptions/flipperbot-war_roster_results'

    subscription = subscriber.get_subscription(subscription=subscription_name)
    if subscription:
        subscriber.delete_subscription(subscription=subscription_name)

    subscriber.create_subscription(name=subscription_name, topic=topic_name)
    subscriber.subscribe(subscription_name, _handle_results)
    print(f'Subscribed to {topic_name}')


def _upload_attachment_to_bucket(filename, data):
    # Upload to GCP bucket
    output_file = f"{date.today()}-{filename}"
    print(f"Writing attachment to: war_roster_screenshots.msf.flipperkid.com/{output_file}")
    bucket = storage_client.get_bucket('war_roster_screenshots.msf.flipperkid.com')
    blob = bucket.blob(output_file)
    blob.upload_from_string(
       data=data,
       content_type=mimetypes.guess_type(filename)[0],
    )


@discord_client.event
async def on_ready():
    channel = _get_channel()
    if not channel:
        print(f'Unable to find channel {GUILD}#{CHANNEL}')
        sys.exit()

    print(f'{discord_client.user} has connected to {GUILD}#{channel.name}!')
    _subscribe_to_results()


@discord_client.event
async def on_message(message):
    if message.guild.name == GUILD and message.channel.name == CHANNEL:
        for attachment in message.attachments:
            data = await attachment.read()
            _upload_attachment_to_bucket(attachment.filename, data)


if __name__ == '__main__':
    discord_client.run(TOKEN)
