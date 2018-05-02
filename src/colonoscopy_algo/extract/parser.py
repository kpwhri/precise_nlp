import re


def depth_to_location(depth: float):
    """
    Convert depth (of polyp) to location in colon
        based on https://training.seer.cancer.gov/colorectal/anatomy/figure/figure1.html
    :param depth:
    :return:
    """
    locations = []
    if depth <= 4:
        locations.append('anus')
    if 4 <= depth <= 17:
        locations.append('rectum')
    if 15 <= depth <= 57:
        locations.append('sigmoid')
    if 57 <= depth <= 82:
        locations.append('descending')
    if 80 <= depth <= 84:  # I made this up
        locations.append('hepatic')
    if 82 <= depth <= 132:
        locations.append('transverse')
    if 130 <= depth <= 134:
        locations.append('splenic')
    if 132 <= depth <= 147:
        locations.append('ascending')
    if 147 <= depth:
        locations.append('cecum')
    return locations


def standardize_locations(lst):
    lookup = {
        'anus': 'anus',
        'anal': 'anus',
        'rectum': 'rectum',
        'rectal': 'rectum',
        'sigmoid': 'sigmoid',
        'descending': 'descending',
        'ascending': 'ascending',
        'hepatic': 'hepatic',
        'transverse': 'transverse',
        'splenic': 'splenic',
        'cecum': 'cecum',
        'cecal': 'cecum',
        'duodenum': 'duodenum',
        'duodenal': 'duodenum',
        'proximal': 'proximal',
        'distal': 'distal',
        'ileocecal': 'ileocecum',
        'ileocecum': 'ileocecum',
        'ic': 'ileocecum',
    }
    res = []
    for el in lst:
        if el not in lookup:
            raise ValueError(f'Unknown location: {el}')
        res.append(lookup[el])
    return res


class NumberConvert:
    VALUES = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    }
    VALUES.update({str(i): i for i in range(10)})

    @staticmethod
    def contains(text, followed_by=None, distance=0, split_on_non_word=False):
        results = []
        if split_on_non_word:
            text = re.split('\W+', text)
        else:
            text = text.split()
        dtext = {x: i for i, x in enumerate(text)}
        for val in set(dtext) & set(NumberConvert.VALUES):
            start = dtext[val] + 1
            if not followed_by or set(followed_by) & set(text[start:start + distance]):
                results.append(NumberConvert.VALUES[val])
        return results