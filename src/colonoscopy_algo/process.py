import csv
import json
import logging
import logging.config
import random
import sys
import warnings

import pandas as pd

import os

import re
import yaml
from collections import defaultdict
from jsonschema import validate

from colonoscopy_algo.const import HIGHGRADE_DYSPLASIA, ANY_VILLOUS, VILLOUS, TUBULAR, TUBULOVILLOUS, ADENOMA_STATUS, \
    ADENOMA_COUNT, LARGE_ADENOMA, ADENOMA_COUNT_ADV, ADENOMA_STATUS_ADV, ADENOMA_DISTAL, ADENOMA_DISTAL_COUNT
from colonoscopy_algo.extract.adenoma import get_adenoma_status, get_adenoma_histology, get_highgrade_dysplasia, \
    get_adenoma_count, has_large_adenoma, get_adenoma_count_advanced, get_adenoma_distal
from colonoscopy_algo.extract.cspy import CspyManager
from colonoscopy_algo.extract.jar import PathManager
from cronkd.util.logger import setup

from colonoscopy_algo.extract.jar import PathManager

logging.config.dictConfig(setup())


ITEMS = [
    ADENOMA_STATUS,
    TUBULOVILLOUS,
    TUBULAR,
    VILLOUS,
    ANY_VILLOUS,
    HIGHGRADE_DYSPLASIA,
    ADENOMA_COUNT,
    ADENOMA_COUNT_ADV,
    ADENOMA_STATUS_ADV,
    ADENOMA_DISTAL,
    ADENOMA_DISTAL_COUNT
]


def process_text(path_text, cspy_text=''):
    pm = PathManager(path_text)
    cm = CspyManager(cspy_text)
    specs, specs_combined, specs_dict = PathManager.parse_jars(path_text)
    tb, tbv, vl = get_adenoma_histology(specs_combined)
    adenoma_count, adenoma_status = get_adenoma_count_advanced(pm)
    aden_dist_count, aden_dist_status = get_adenoma_distal(pm)
    return {
        ADENOMA_STATUS: get_adenoma_status(specs),
        TUBULAR: tb,
        TUBULOVILLOUS: tbv,
        VILLOUS: vl,
        ANY_VILLOUS: tbv or vl,
        HIGHGRADE_DYSPLASIA: get_highgrade_dysplasia(specs),
        ADENOMA_COUNT: get_adenoma_count(specs),
        LARGE_ADENOMA: has_large_adenoma(pm, cm),
        ADENOMA_COUNT_ADV: adenoma_count,
        ADENOMA_STATUS_ADV: adenoma_status,
        ADENOMA_DISTAL: aden_dist_status,
        ADENOMA_DISTAL_COUNT: aden_dist_count,
    }


def get_data(filetype, path, identifier, path_text=None, cspy_text=None,
             limit=None, truth=None, text=None, requires_cspy_text=False):
    """

    :param filetype:
    :param path:
    :param identifier:
    :param path_text:
    :param cspy_text:
    :param limit:
    :param truth:
    :param text: deprecated
    :return:
    """
    if text:
        warnings.warn('Use `path_text` rather than `text`.',
                      DeprecationWarning
                      )
        path_text = text

    if path and os.path.isdir(path):
        for fn in os.listdir(path):
            get_data(filetype, os.path.join(path, fn), identifier, path_text, cspy_text, truth)
    else:
        if 'DataFrame' in str(type(filetype)):
            df = filetype
        elif filetype == 'csv':
            df = pd.read_csv(path, encoding='latin1')
        elif filetype == 'sas':
            df = pd.read_sas(path, encoding='latin1')
        elif filetype == 'h5':
            df = pd.read_hdf(path, 'data')
        else:
            raise ValueError(f'Unrecognized filetype: {filetype}')
        # ensure no nan
        if cspy_text:
            df[cspy_text].fillna('', inplace=True)
        df[path_text].fillna('', inplace=True)
        for row in df.itertuples():
            name = getattr(row, identifier)
            if limit and name not in limit:
                continue
            if cspy_text and requires_cspy_text and not getattr(row, cspy_text):
                continue  # skip missing records
            yield (name,
                   getattr(row, path_text),
                   getattr(row, cspy_text) if cspy_text else '',
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
    logging.info(f'{identifier}: {value.upper()}')
    d[label].append(identifier)
    return 1


def process(data, truth, errors=None, output=None, outfile=None):
    score = defaultdict(lambda: [0, 0, 0, 0])  # TP, FP, FN, TN
    fps = defaultdict(list)
    fns = defaultdict(list)
    if outfile:
        fh = open(outfile, 'w', newline='')
        outfile = csv.writer(fh)
    for i, (identifier, path_text, cspy_text, truth_values) in enumerate(get_data(**data, truth=truth)):
        if pd.isnull(path_text):
            ve = ValueError('Text cannot be missing/none')
            print(ve)
            continue
        if outfile and i == 0:
            row = ['row', 'identifier']  # header
            for label in truth_values:
                row.append(f'{label}_true')
                row.append(f'{label}_pred')
            outfile.writerow(row)
        print(f'Starting: {identifier}')
        res = process_text(path_text, cspy_text)
        row = [i, identifier]
        for label in truth_values:
            truth_item = clean_truth(truth_values[label])
            row.append(res[label])
            row.append(truth_item)
            if res[label] == truth_item == 0:
                logging.info(f'{identifier}: TN')
                score[label][3] += 1
            elif res[label] == truth_item:
                logging.info(f'{identifier}: TP')
                score[label][0] += 1
            elif truth_item == 1:
                score[label][2] += add_identifier(identifier, fns, label, errors, 'fn')
            else:
                score[label][1] += add_identifier(identifier, fps, label, errors, 'fp')
        if outfile:
            outfile.writerow(row)
    output_results(score, truth, fps, fns, **output if output else dict())
    if outfile:
        fh.close()


def output_results(score, truth, fps, fns, max_false=5):
    for label in truth:
        print(f'Label: {label}')
        print('TP \tFP \tFN \t TN')
        print('\t'.join(str(x) for x in score[label]))
        print(f'PPV {calculate_score(score[label][0], score[label][1])}')
        print(f'Rec {calculate_score(score[label][0], score[label][2])}')
        print(f'Spc {calculate_score(score[label][3], score[label][1])}')

        if max_false:
            print(f'FPs: {random.sample(fps[label], min(max_false, len(fps[label])))}')
            print(f'FNs: {random.sample(fns[label], min(max_false, len(fns[label])))}')


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
                    'cspy_text': {'type': 'string'},
                    'requires_cspy_text': {'type': 'boolean'},
                    'path_text': {'type': 'string'},
                    'text': {'type': 'string'},  # assumed to be path_text
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
            },
            'output': {
                'type': 'object',
                'properties': {
                    'max_false': {'type': 'number'}
                }
            },
            'outfile': {
                'type': 'string'
            },
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
