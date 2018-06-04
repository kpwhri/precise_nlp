import re

from colonoscopy_algo.const.enums import Histology


def append_str(lst, el):
    lst.extend([el] if isinstance(el, str) else el)


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


class StandardTerminology:
    LOCATIONS = {
        'anus': 'anus',
        'anal': 'anus',
        'rectum': 'rectum',
        'rectal': 'rectum',
        'rectosigmoid': ['rectum', 'sigmoid'],
        'sigmoid': 'sigmoid',
        'sig': 'sigmoid',
        'sc': 'sigmoid',
        'dc': 'descending',
        'descending': 'descending',
        'descenging': 'descending',
        'ascending': 'ascending',
        'ac': 'ascending',
        'asend': 'ascending',
        'hf': 'hepatic',
        'hepatic': 'hepatic',
        'transverse': 'transverse',
        'tc': 'transverse',
        'splenic': 'splenic',
        'cecum': 'cecum',
        'cecal': 'cecum',
        'right': 'proximal',
        'proximal': 'proximal',
        'left': 'distal',
        'distal': 'distal',
        'ileocecal': 'cecum',
        'ileocecum': 'cecum',
        'ic': 'cecum',
        'anorectum': ['anus', 'rectum'],
        'anorectal': ['anus', 'rectum'],
        # small intestine
        'duodenum': 'duodenum',
        'duodenal': 'duodenum',
        'jejunum': 'jejunum',
        'jejunal': 'jejunum',
        'ileum': 'ileum',
        'ileal': 'ileum',
        # stomach
        'gastric': 'stomach',
        'stomach': 'stomach',
        # random
        'random': 'random'
    }

    COLON = {
        'anus',
        'rectum',
        'sigmoid',
        'descending',
        'ascending',
        'hepatic',
        'transverse',
        'splenic',
        'cecum',
        'proximal',
        'distal',
        'ileocecum',
    }

    HISTOLOGY = {
        'tubular': Histology.TUBULAR,
        'tubulovillous': Histology.TUBULOVILLOUS,
        'villous': Histology.VILLOUS
    }

    @classmethod
    def standardize_locations(cls, lst, colon_only=False):
        res = []
        for el in lst:
            try:
                loc = cls.LOCATIONS[el]
            except KeyError:
                raise ValueError(f'Unknown location: {el}')
            if not colon_only or loc in cls.COLON:
                append_str(res, cls.LOCATIONS[el])
        return res

    @classmethod
    def histology(cls, item):
        try:
            return cls.HISTOLOGY[item]
        except KeyError:
            raise ValueError(f'Unknown histology: {item}')

    @classmethod
    def filter_colon(cls, lst):
        return cls.standardize_locations(lst, colon_only=True)


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
