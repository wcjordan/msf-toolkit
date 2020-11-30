import csv
import io
import json
import os
from datetime import date

from dotenv import load_dotenv
from google.cloud import pubsub_v1, storage, vision
import sentry_sdk
from sentry_sdk.integrations.gcp import GcpIntegration

from parse import parse_annotations
from vision_api import text_detection

load_dotenv()
sentry_sdk.init(
    os.getenv('SENTRY_URL'),
    integrations=[GcpIntegration()],
    traces_sample_rate=1.0
)

publisher = pubsub_v1.PublisherClient()
storage_client = storage.Client()
vision_client = vision.ImageAnnotatorClient()


def extract_war_breakdown(event, context):
    '''
    Deploy with:
    gcloud functions deploy extract_war_breakdown --runtime python38 --trigger-bucket war_roster_screenshots.msf.flipperkid.com

    When pasting CSV to sheets, these instructions are useful
    https://webapps.stackexchange.com/a/100790
    '''
    print(f"Event ID: {context.event_id}, type: {context.event_type}")
    print(f"Time created: {event['timeCreated']}, updated: {event['updated']}")

    bucket = event['bucket']
    if bucket != 'war_roster_screenshots.msf.flipperkid.com':
        raise Exception('Expected source bucket to be war_roster_screenshots.msf.flipperkid.com')
    filename = event['name']
    print(f"Processing image: {bucket}/{filename}")

    # Call vision API & process response
    image = vision.Image(
        source=vision.ImageSource(gcs_image_uri=f"gs://{bucket}/{filename}")
    )
    annotations = text_detection(image)
    results = parse_annotations(annotations)

    # Write CSV
    csv_output = io.StringIO()
    csv_writer = csv.writer(csv_output)
    for player in results:
        csv_writer.writerow(player)

    # Upload results to GCP bucket
    output_file = f"{filename}-{date.today()}.csv"
    print(f"Writing results to: war_rosters.msf.flipperkid.com/{output_file}")
    bucket = storage_client.get_bucket('war_rosters.msf.flipperkid.com')
    blob = bucket.blob(output_file)
    blob.upload_from_string(
       data=csv_output.getvalue(),
       content_type='text/csv',
    )
    csv_output.close()

    print(f"Publishing results to: projects/flipperkid-default/topics/war_roster_results")
    topic_name = 'projects/flipperkid-default/topics/war_roster_results'
    publisher.publish(topic_name, output_file.encode('utf-8'))
