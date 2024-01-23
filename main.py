import json
import os
import sys
import traceback

import pulsar
import pygogo as gogo
from plexapi.server import PlexServer
from plexapi.exceptions import NotFound


def main():
    logger.info("Starting SAD Destroyer")
    client = pulsar.Client(f"pulsar://{os.environ['PULSAR_SERVER']}")
    consumer = client.subscribe(os.environ['PULSAR_TOPIC'], os.environ['PULSAR_SUBSCRIPTION'])

    while True:
        msg = consumer.receive()
        message_body = None  # set here to make my IDE happy
        try:
            # decode from bytes, encode with backslashes removed, decode back to a string, then load it as a
            # python native
            message_body = json.loads(msg.data().decode().encode('latin1', 'backslashreplace').decode('unicode-escape'))
            logger.info(f"Received message '{message_body}' id='{msg.message_id()}'")
            process_message(message_body)
            consumer.acknowledge(msg)
            logger.info(f"Message id='{msg.message_id()}' processed successfully")
        except Exception as e:  # noqa: E722
            # Message failed to be processed
            consumer.negative_acknowledge(msg)
            logger.error("A message could not be processed",
                         extra={'message_body': message_body, 'exception': e, 'stack_trace': traceback.format_exc()})


def process_message(message_body):
    logger.info("Processing message", extra={'message_body': message_body})
    plex_key = message_body['plexKey']
    delete_from_plex(plex_key=plex_key)
    logger.info("Scheduling a search request")
    send_search_request()
    return None


def get_movie_library():
    plex = get_plex_client()
    movies = plex.library.section('Movies')
    return movies


def get_plex_client():
    baseurl = os.getenv("PLEX_URL")
    token = os.getenv("PLEX_TOKEN")
    plex = PlexServer(baseurl, token)
    return plex


def send_search_request():
    # Create a Pulsar client
    client = pulsar.Client(f'pulsar://{os.environ["PULSAR_SERVER"]}')

    # Create a producer on the topic 'plex-search'
    producer = client.create_producer(os.environ['PULSAR_SEARCH_TOPIC'])

    # Create a message
    message = ['all']
    message_json = json.dumps(message).encode('utf-8')

    # Send the message
    producer.send(message_json)

    # Close the producer and client to free up resources
    producer.close()
    client.close()


def pre_flight_checks():
    # Ensure that the required environment variables are set.
    required_env_vars = [
        'PULSAR_SERVER',
        'PULSAR_SEARCH_TOPIC',
        'PLEX_URL',
        'PLEX_TOKEN',
        'PULSAR_TOPIC',
        'PULSAR_SUBSCRIPTION',
    ]

    for env_var in required_env_vars:
        if env_var not in os.environ:
            sys.exit(f"Missing required environment variable: {env_var}")


def delete_from_plex(*, plex_key):
    # Given a plex key, delete the item from plex.  Plex key is the ratingKey of the media.
    plex = get_plex_client()
    try:
        item = plex.fetchItem(ekey=int(plex_key))
        logger.info(f"Deleting '{item.title}'")
        dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        if not dry_run:
            item.delete()
        else:
            logger.info("Dry run is enabled, not deleting")
    except NotFound:
        logger.warning(f"Item with plex key '{plex_key}' not found")


if __name__ == '__main__':
    logger = gogo.Gogo('sad.destroy', low_formatter=gogo.formatters.structured_formatter,
                       low_level=os.getenv("SAD_LOG_LEVEL", "INFO")).get_logger()
    pre_flight_checks()
    main()
