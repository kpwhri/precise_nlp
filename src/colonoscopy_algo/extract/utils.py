import re
from enum import Enum

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
    SPECIFYING_LOCATIONS = [  # locations which can just be adjectives
        'right', 'left',
        'distal', 'proximal'
    ]
    # https://www.cancer.gov/publications/dictionaries/cancer-terms/def/distal-colon
    # technically, does not include rectum, though I've included it
    RECTAL_LOCATIONS = ['rectum']
    # TODO: remove 'rectum' from DISTAL_LOCATIONS
    # https://www.ncbi.nlm.nih.gov/pubmedhealth/PMHT0022241/
    DISTAL_LOCATIONS = [
        'descending', 'sigmoid', 'distal',
        'splenic', 'left', 'rectum'
    ]
    PROXIMAL_LOCATIONS = [
        'proximal', 'ascending',
        'transverse', 'cecum', 'hepatic', 'right'
    ]

    LOCATIONS = {
        'anus': 'anus',
        'anal': 'anus',
        'rectum': 'rectum',
        'rectal': 'rectum',
        'rectosigmoid': ['rectum', 'sigmoid'],
        'rectosig': ['rectum', 'sigmoid'],
        'sigmoid': 'sigmoid',
        'sig': 'sigmoid',
        'sc': 'sigmoid',
        'dc': 'descending',
        'descending': 'descending',
        'descenging': 'descending',
        'ascending': 'ascending',
        'ac': 'ascending',
        'asend': 'ascending',
        'ascend': 'ascending',
        'hf': 'hepatic',
        'hepatic': 'hepatic',
        'transverse': 'transverse',
        'transv': 'transverse',
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
        'bowel': 'bowel',  # assume to be small
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
        'tubulovil': Histology.TUBULOVILLOUS,
        'villotubular': Histology.TUBULOVILLOUS,
        'villous': Histology.VILLOUS,
        'villiform': Histology.VILLOUS,
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
        'a': 1, 'an': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    }
    VALUES.update({str(i): i for i in range(10)})

    @staticmethod
    def contains(text, followed_by=None, distance=0, split_on_non_word=False):
        results = []
        if split_on_non_word:
            text = re.split(r'\W+', text)
        else:
            text = text.split()
        dtext = {x: i for i, x in enumerate(text)}
        for val in set(dtext) & set(NumberConvert.VALUES):
            start = dtext[val] + 1
            if not followed_by or set(followed_by) & set(text[start:start + distance]):
                results.append(NumberConvert.VALUES[val])
        return results


class Prep(Enum):
    ADEQUATE = 0
    INADEQUATE = 1
    UNKNOWN = 99


class ColonPrep:
    VALUES = {
        'excellent': Prep.ADEQUATE,
        'well': Prep.ADEQUATE,
        'good': Prep.ADEQUATE,
        'moderate': Prep.ADEQUATE,
        'adequate': Prep.ADEQUATE,
        'optimal': Prep.ADEQUATE,
        'fair': Prep.INADEQUATE,
        'poor': Prep.INADEQUATE,
        'inadequate': Prep.INADEQUATE,
        'suboptimal': Prep.INADEQUATE,
    }
    REGEX = '|'.join(VALUES.keys())


class Indication(Enum):
    DIAGNOSTIC = 0
    SURVEILLANCE = 1
    SCREENING = 2
    UNKNOWN = 99


IndicationPriority = (
    Indication.DIAGNOSTIC,
    Indication.SURVEILLANCE,
    Indication.SCREENING,
)


class Extent(Enum):
    COMPLETE = 0
    INCOMPLETE = 1
    UNKNOWN = 99
