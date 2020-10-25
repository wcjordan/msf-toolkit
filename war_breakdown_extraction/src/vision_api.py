import io
import json
import os
import sys

from google.cloud import vision

from parse import convert_annotation

vision_client = vision.ImageAnnotatorClient()


def text_detection(image):
    response = vision_client.document_text_detection(image=image)
    return [convert_annotation(item) for item in response.text_annotations]


# Run with: GOOGLE_APPLICATION_CREDENTIALS="/Users/jordan/.gcp/gac.json" python vision_api.py
if __name__ == '__main__':
    file_name = os.path.abspath(f"../test_data/screenshots/{sys.argv[1]}.png")

    # Loads the image into memory
    with io.open(file_name, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    annotations = text_detection(image)

    out_filename = os.path.abspath(f"../test_data/vision_api_annotations/{sys.argv[1]}.json")
    with open(out_filename, 'w') as outfile:
        json.dump(annotations, outfile, indent=2)
