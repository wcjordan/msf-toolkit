import json
from datetime import date

from google.cloud import storage, vision

from parse import parse_annotations
from vision_api import text_detection

storage_client = storage.Client()
vision_client = vision.ImageAnnotatorClient()


def extract_war_breakdown(event, context):
    '''
    Deploy with:
    gcloud functions deploy extract_war_breakdown --runtime python38 --trigger-bucket war_roster_screenshots.msf.flipperkid.com
    '''
    print(f"Event ID: {context.event_id}, type: {context.event_type}")
    print(f"Time created: {event['timeCreated']}, updated: {event['updated']}")

    bucket = event['bucket']
    if bucket != 'war_roster_screenshots.msf.flipperkid.com':
        raise Exception('Expected source bucket to be war_roster_screenshots.msf.flipperkid.com')
    filename = event['name']
    print(f"Processing image: {bucket}/{filename}")

    image = vision.Image(
        source=vision.ImageSource(gcs_image_uri=f"gs://{bucket}/{filename}")
    )

    annotations = text_detection(image)
    results = parse_annotations(annotations)

    output_file = f"{filename}-{date.today()}.json"
    print(f"Writing results to: war_rosters.msf.flipperkid.com/{output_file}")
    bucket = storage_client.get_bucket('war_rosters.msf.flipperkid.com')
    blob = bucket.blob(output_file)
    blob.upload_from_string(
       data=json.dumps(results, indent=2),
       content_type='application/json',
    )
