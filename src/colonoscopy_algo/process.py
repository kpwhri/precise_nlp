import json
import random
import sys
import pandas as pd

import os

import re
import yaml
from collections import defaultdict
from jsonschema import validate

from colonoscopy_algo.extract.adenoma import get_adenoma_status, get_adenoma_histology


ITEMS = [
    'adenoma_status',
    'tubulovillous',
    'tubular',
    'villous',
    'any_villous'
]


def process_text(text):
    specimens = [x.lower() for x in re.split(r'\W[A-Z]\)', text)]
    specimens_combined = defaultdict(list)
    it = iter(['A'] + re.split(r'(?:^|\W)([A-Z])\)', text))
    for x in it:
        specimens_combined[x.lower()].append(next(it).lower())
    specimens_combined = [' '.join(spec) for spec in specimens_combined.values()]
    tb, tbv, vl = get_adenoma_histology(specimens_combined)
    return {
        'adenoma_status': get_adenoma_status(specimens),
        'tubular': tb,
        'tubulovillous': tbv,
        'villous': vl,
        'any_villous': tbv or vl
    }


def get_data(filetype, path, identifier, text, limit=None, truth=None):
    if path and os.path.isdir(path):
        for fn in os.listdir(path):
            get_data(filetype, os.path.join(path, fn), identifier, text, truth)
    else:
        if 'DataFrame' in str(type(filetype)):
            df = filetype
        elif filetype == 'csv':
            df = pd.read_csv(path, encoding='latin1')
        elif filetype == 'sas':
            df = pd.read_sas(path, encoding='latin1')
        else:
            raise ValueError(f'Unrecognized filetype: {filetype}')
        for row in df.itertuples():
            name = getattr(row, identifier)
            if limit and name not in limit:
                continue
            yield (name, getattr(row, text),
                   {x: getattr(row, truth[x]) for x in truth} if truth else None)


def clean_truth(x):
    if isinstance(x, str):
        if x[0].lower() == 'y':
            return 1
        if x[0].lower() == 'n':
            return 0
    return x


def add_identifier(identifier, d, label, errors, value='fp'):
    """
    Exlude errors in the gold standard
    :param value: 'fp' or 'fn'
    :param identifier:
    :param d:
    :param label:
    :param errors:
    :return:
    """
    try:
        if identifier in errors[label][value.lower()]:
            return 0
    except KeyError:
        pass
    except TypeError:
        pass
    print(f'{identifier}: {value.upper()}')
    d[label].append(identifier)
    return 1


def process(data, truth, errors=None):
    score = defaultdict(lambda: [0, 0, 0, 0])  # TP, FP, FN, TN
    fps = defaultdict(list)
    fns = defaultdict(list)
    for identifier, text, truth_values in get_data(**data, truth=truth):
        res = process_text(text)
        for label in truth_values:
            truth_item = clean_truth(truth_values[label])
            if res[label] == truth_item == 0:
                print(f'{identifier}: TN')
                score[label][3] += 1
            elif res[label] == truth_item:
                print(f'{identifier}: TP')
                score[label][0] += 1
            elif truth_item == 1:
                score[label][2] += add_identifier(identifier, fns, label, errors, 'fn')
            else:
                score[label][1] += add_identifier(identifier, fps, label, errors, 'fp')
    for label in truth:
        print(f'Label: {label}')
        print('TP \tFP \tFN \t TN')
        print('\t'.join(str(x) for x in score[label]))
        print(f'PPV {calculate_score(score[label][0], score[label][1])}')
        print(f'Rec {calculate_score(score[label][0], score[label][2])}')
        print(f'Spc {calculate_score(score[label][3], score[label][1])}')

        print(f'FPs: {random.sample(fps[label], min(5, len(fps[label])))}')
        print(f'FNs: {random.sample(fns[label], min(5, len(fns[label])))}')


def calculate_score(num, denom):
    if not num + denom:
        return 'nan'
    return num / (num + denom)


def process_config():
    schema = {
        'type': 'object',
        'properties': {
            'data': {
                'type': 'object',
                'properties': {
                    'filetype': {'type': 'string'},
                    'path': {'type': 'string'},
                    'identifier': {'type': 'string'},
                    'text': {'type': 'string'},
                    'limit': {'type': 'string'},
                }
            },
            'truth': {
                'type': 'object',
                'properties': {
                    item: {'type': 'string'} for item in ITEMS
                }
            },
            'errors': {
                'type': 'object',
                'properties': {
                    item: {
                        'type': 'object',
                        'properties': {
                            'fp': {'type': 'array', 'items': {'type': 'string'}},
                            'fn': {'type': 'array', 'items': {'type': 'string'}},
                        }
                    } for item in ITEMS
                }
            }
        }
    }
    conf_fp = sys.argv[1]
    with open(conf_fp) as conf:
        if conf_fp.endswith('json'):
            config = json.load(conf)
        elif conf_fp.endswith('yaml'):
            config = yaml.load(conf)
        else:
            raise ValueError('Unrecognized config file type "{}". Expected "yaml" or "json".'.format(
                os.path.splitext(conf_fp)[-1]
            ))
    validate(config, schema)
    process(**config)


if __name__ == '__main__':
    process_config()
