import json
import sys

X_MIN_COORD = 0
X_MAX_COORD = 1
Y_MIN_COORD = 2
Y_MAX_COORD = 3
PIXEL_MARGIN = 20
ROW_MARGIN = 10


def _load_json_response(filename):
    with open(filename) as file:
        return json.load(file)


def _y_center_of_text(bounds):
    return (bounds[Y_MIN_COORD] + bounds[Y_MAX_COORD]) / 2


def convert_annotation(annotation):
    # Handles converting annotations to a common format for both dictionary and class types
    if type(annotation) is dict:
        coords = [coord for coord in annotation['boundingPoly']['vertices']]
        x_coords = [coord['x'] for coord in coords]
        y_coords = [coord['y'] for coord in coords]
        return {
            'description': annotation['description'],
            'bounds': (min(x_coords), max(x_coords), min(y_coords), max(y_coords)),
        }

    coords = [coord for coord in annotation.bounding_poly.vertices]
    x_coords = [coord.x for coord in coords]
    y_coords = [coord.y for coord in coords]
    return {
        'description': annotation.description,
        'bounds': (min(x_coords), max(x_coords), min(y_coords), max(y_coords)),
    }


def _extract_row_bounds(power_bounds):
    '''
    Find the start X coord of each row
    First extract the farthest to the left bounding boxes for the Collection Power text
    Then drop any matches which are more than PIXEL_MARGIN beyond that text
    Use the remaining bounding boxes to determine the start and end Y coordinate for each row
    '''
    max_x = max([coords[X_MAX_COORD] for coords in power_bounds])
    row_start_ys = [bound[Y_MIN_COORD] for bound in power_bounds if bound[X_MAX_COORD] > max_x - PIXEL_MARGIN]
    row_start_ys.sort()

    max_height = 0
    row_bounds = []
    for idx in range(len(row_start_ys)):
        start = row_start_ys[idx]
        if idx + 1 < len(row_start_ys):
            end = row_start_ys[idx+1] - ROW_MARGIN
            max_height = max(max_height, end - start)
            row_bounds.append((start, end))
        else:
            row_bounds.append((start, start+max_height))
    return row_bounds


def _group_rows(all_row_bounds, annotations):
    '''
    Group the annotations according to the row bounds they fall within
    '''
    row_groups = [[] for idx in range(len(all_row_bounds))]
    for annotation in annotations:
        for row_idx, row_bounds in enumerate(all_row_bounds):
            bounds = annotation['bounds']
            text_start = bounds[Y_MIN_COORD]
            if text_start > row_bounds[0] and text_start <= row_bounds[1]:
                row_groups[row_idx].append(annotation)
    return row_groups


def _partition_left_right(row, min_x_bound, max_x_bound):
    x_start_divider = (min_x_bound + max_x_bound) / 2
    left_text = [item for item in row if item['bounds'][X_MIN_COORD] < x_start_divider]
    right_text = [item for item in row if item['bounds'][X_MIN_COORD] >= x_start_divider]

    if len(right_text) == 3 and right_text[1]['description'] == ',':
        descriptions = [item['description'] for item in right_text]
        bounds = [item['bounds'] for item in right_text]
        right_text = [{
            'description': ''.join(descriptions),
            'bounds':[
                min([item[X_MIN_COORD] for item in bounds]),
                max([item[X_MAX_COORD] for item in bounds]),
                min([item[Y_MIN_COORD] for item in bounds]),
                max([item[Y_MAX_COORD] for item in bounds]),
            ],
        }]
        print(left_text)
        print(right_text)
    assert len(right_text) == 1

    return left_text, right_text


def _extract_row_text(row, min_x_bound, max_x_bound):
    '''
    Extract the pertinent data from the row grouping
    First split the annotations into the left side (name, rank, level
    and the right side (collection power)
    '''
    left_text, right_text = _partition_left_right(row, min_x_bound, max_x_bound)

    # Filter out any items on the left_text which are below the CP on the right
    right_y_center = _y_center_of_text(right_text[0]['bounds'])
    filtered_left = [item for item in left_text if _y_center_of_text(item['bounds']) < right_y_center]

    # Find a divider to split the left_text into name vs rank & level
    y_centers = [_y_center_of_text(item['bounds']) for item in filtered_left]
    y_centers.sort()
    middle_y = (y_centers[0] + y_centers[-1]) / 2

    name = []
    rank_level = []
    for item in filtered_left:
        text_center = _y_center_of_text(item['bounds'])
        if text_center < middle_y:
            name.append(item)
        else:
            rank_level.append(item)

    name.sort(key=lambda item: item['bounds'][X_MIN_COORD])
    rank_level.sort(key=lambda item: item['bounds'][X_MIN_COORD])

    result = [
        # Name
        ' '.join([item['description'] for item in name]),
    ]
    # Add Rank, omit Level
    result.append(rank_level[1]['description'])

    # CP
    # Fix up numeric issues by switching decimals to commas and Zs to 7s
    result.append(' '.join([item['description'] for item in right_text]).replace('Z', '7').replace('.', '').replace(',', ''))
    return result


def parse_annotations(annotations):
    power_bounds = [item['bounds'] for item in annotations if item['description'] == 'POWER']
    all_row_bounds = _extract_row_bounds(power_bounds)
    row_groups = _group_rows(all_row_bounds, annotations)

    # Extract the min X from each row group and take the max among those
    # Filter any text which is more than PIXEL_MARGIN before that bound
    # Also compute the max X for partitioning data as part of the text extraction
    min_x_bound = max([min([annotation['bounds'][X_MIN_COORD]
                            for annotation in group])
                       for group in row_groups])
    row_groups = [[annotation for annotation in group
                   if annotation['bounds'][X_MIN_COORD] > min_x_bound - PIXEL_MARGIN]
                  for group in row_groups]
    max_x_bound = max([max([annotation['bounds'][X_MAX_COORD]
                            for annotation in group])
                       for group in row_groups])

    return [_extract_row_text(row, min_x_bound, max_x_bound) for row in row_groups]


if __name__ == '__main__':
    annotations = _load_json_response(f"../test_data/vision_api_annotations/{sys.argv[1]}.json")
    results = parse_annotations(annotations)
    print(json.dumps(results, indent=2))
