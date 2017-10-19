import json
import sys
import pandas as pd

import os
import yaml
from jsonschema import validate

from colonoscopy_algo.extract.adenoma import get_adenoma_status


def process_text(text):
    return get_adenoma_status(text)


def get_data(filetype, path, identifier, text, truth):
    if os.path.isdir(path):
        for fn in os.listdir(path):
            get_data(filetype, os.path.join(path, fn), identifier, text, truth)
    else:
        if filetype == 'csv':
            df = pd.read_csv(path, encoding='latin1')
            for row in df.itertuples():
                yield getattr(row, identifier), getattr(row, text), getattr(row, truth)


def clean_truth(x):
    if isinstance(x, str):
        if x[0].lower() == 'y':
            return 1
        if x[0].lower() == 'n':
            return 0
    return x


def process(data):
    score = [0, 0, 0, 0]  # TP, FP, FN, TN
    fps = []
    fns = []
    for identifier, text, truth in get_data(**data):
        truth = clean_truth(truth)
        res = process_text(text)
        if res == truth == 0:
            print(f'{identifier}: TN')
            score[3] += 1
        elif res == truth:
            print(f'{identifier}: TP')
            score[0] += 1
        elif truth == 1:
            print(f'{identifier}: FN')
            fns.append(identifier)
            score[2] += 1
        else:
            print(f'{identifier} FP')
            fps.append(identifier)
            score[1] += 1
    print('TP \tFP \tFN \t TN')
    print('\t'.join(str(x) for x in score))
    print(f'PPV  {score[0] / (score[0] + score[1])}')
    print(f'Rec {score[0] / (score[0] + score[2])}')
    print(f'Spc {score[3] / (score[3] + score[1])}')

    print(f'FPs: {fps[:5]}')
    print(f'FNs: {fns[:5]}')


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
                    'truth': {'type': 'string'}
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
