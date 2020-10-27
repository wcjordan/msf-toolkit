import json
import sys

X_MIN_COORD = 0
X_MAX_COORD = 1
Y_MIN_COORD = 2
Y_MAX_COORD = 3
PIXEL_MARGIN = 20
ROW_MARGIN = 10
SUBROW_MARGIN = 5


def _load_json_response(filename):
    with open(filename) as file:
        return json.load(file)


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
    # Find the farthest to the left bounding boxes
    # and drop any matches which are more than PIXEL_MARGIN out of alignment
    # end up w/ the start Y coordinate for each row
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
    row_groups = [[] for idx in range(len(all_row_bounds))]
    for annotation in annotations:
        for row_idx, row_bounds in enumerate(all_row_bounds):
            bounds = annotation['bounds']
            text_start = bounds[Y_MIN_COORD]
            if text_start > row_bounds[0] and text_start <= row_bounds[1]:
                row_groups[row_idx].append(annotation)
    return row_groups


def _center_of_text(bounds):
    return (bounds[Y_MIN_COORD] + bounds[Y_MAX_COORD]) / 2


def _extract_row_text(row):
    y_center = [_center_of_text(item['bounds']) for item in row]
    y_center.sort()

    subrow_start = None
    subrows_ys = []
    for pos in y_center:
        if subrow_start is None:
            subrow_start = pos
        elif pos - subrow_start > SUBROW_MARGIN:
            subrows_ys.append((subrow_start, pos))
            subrow_start = pos
    subrows_ys.append((subrow_start, float('inf')))

    if len(subrows_ys) < 3:
        raise Exception(f"Expected at least 3 subrows! Found {len(subrows_ys)}")

    subrows = [[] for idx in range(3)]
    for item in row:
        for row_idx, row_bounds in enumerate(subrows_ys):
            if row_idx > 2:
                continue
            text_center = _center_of_text(item['bounds'])
            if text_center >= row_bounds[0] and text_center < row_bounds[1]:
                subrows[row_idx].append(item)
    for subrow in subrows:
        subrow.sort(key=lambda item: item['bounds'][X_MIN_COORD])

    result = [
        # Name
        ' '.join([item['description'] for item in subrows[0]]),
    ]
    # Add Rank, omit Level
    result.append(subrows[1][1]['description'])

    # CP
    # Fix up numeric issues by switching decimals to commas and Zs to 7s
    result.append(' '.join([item['description'] for item in subrows[2]]).replace('Z', '7').replace('.', '').replace(',', ''))
    return result


def parse_annotations(annotations):
    power_bounds = [item['bounds'] for item in annotations if item['description'] == 'POWER']
    all_row_bounds = _extract_row_bounds(power_bounds)
    row_groups = _group_rows(all_row_bounds, annotations)

    # Extract the min X from each row group and take the max among those
    # Filter any text which is more than PIXEL_MARGIN before that bound
    min_x_bound = max([min([annotation['bounds'][X_MIN_COORD]
                            for annotation in group])
                       for group in row_groups])
    row_groups = [[annotation for annotation in group
                   if annotation['bounds'][X_MIN_COORD] > min_x_bound - PIXEL_MARGIN]
                  for group in row_groups]

    return [_extract_row_text(row) for row in row_groups]


if __name__ == '__main__':
    annotations = _load_json_response(f"../test_data/vision_api_annotations/{sys.argv[1]}.json")
    results = parse_annotations(annotations)
    print(json.dumps(results, indent=2))
