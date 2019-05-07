import csv
import json
import logging
import logging.config
import random
import sys
import warnings

import pandas as pd

import os

import yaml
from collections import defaultdict, Counter
from jsonschema import validate

from colonoscopy_algo.const.cspy import INDICATION, FINDINGS, BOWEL_PREP, EXTENT, NUM_POLYPS
from colonoscopy_algo.const.path import HIGHGRADE_DYSPLASIA, ANY_VILLOUS, VILLOUS, TUBULAR, TUBULOVILLOUS, \
    ADENOMA_STATUS, \
    ADENOMA_COUNT, LARGE_ADENOMA, ADENOMA_COUNT_ADV, ADENOMA_STATUS_ADV, ADENOMA_DISTAL, ADENOMA_DISTAL_COUNT, \
    ADENOMA_PROXIMAL_COUNT, ADENOMA_PROXIMAL, ADENOMA_RECTAL_COUNT, ADENOMA_RECTAL, ADENOMA_UNKNOWN_COUNT, \
    ADENOMA_UNKNOWN, PROXIMAL_VILLOUS, DISTAL_VILLOUS, RECTAL_VILLOUS, UNKNOWN_VILLOUS, SIMPLE_HIGHGRADE_DYSPLASIA
from colonoscopy_algo.const.enums import Location
from colonoscopy_algo.doc_parser import parse_file
from colonoscopy_algo.extract.algorithm import get_adenoma_status, get_adenoma_histology, get_highgrade_dysplasia, \
    get_adenoma_count, has_large_adenoma, get_adenoma_count_advanced, get_adenoma_distal, get_adenoma_proximal, \
    get_adenoma_rectal, get_adenoma_unknown, get_villous_histology, has_dysplasia
from colonoscopy_algo.extract.cspy import CspyManager
from colonoscopy_algo.extract.path import PathManager
from cronkd.util.logger import setup


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
    ADENOMA_DISTAL_COUNT,
    ADENOMA_PROXIMAL,
    ADENOMA_PROXIMAL_COUNT,
    PROXIMAL_VILLOUS,
    DISTAL_VILLOUS,
    RECTAL_VILLOUS,
    UNKNOWN_VILLOUS,
    SIMPLE_HIGHGRADE_DYSPLASIA,
]


def process_text(path_text='', cspy_text=''):
    pm = PathManager(path_text)
    cm = CspyManager(cspy_text)
    data = {}
    if pm:
        specs, specs_combined, specs_dict = PathManager.parse_jars(path_text)
        tb, tbv, vl = get_adenoma_histology(pm)
        adenoma_count, adenoma_status = get_adenoma_count_advanced(pm)
        aden_dist_count, aden_dist_status = get_adenoma_distal(pm)
        aden_prox_count, aden_prox_status = get_adenoma_proximal(pm)
        aden_rect_count, aden_rect_status = get_adenoma_rectal(pm)
        aden_unk_count, aden_unk_status = get_adenoma_unknown(pm)
        data.update({
            ADENOMA_STATUS: get_adenoma_status(specs),
            TUBULAR: tb,
            TUBULOVILLOUS: bool(tbv),
            VILLOUS: bool(vl),
            ANY_VILLOUS: get_villous_histology(pm),
            PROXIMAL_VILLOUS: get_villous_histology(pm, Location.PROXIMAL),
            DISTAL_VILLOUS: get_villous_histology(pm, Location.DISTAL),
            RECTAL_VILLOUS: get_villous_histology(pm, Location.RECTAL),
            UNKNOWN_VILLOUS: get_villous_histology(pm, Location.UNKNOWN),
            SIMPLE_HIGHGRADE_DYSPLASIA: get_highgrade_dysplasia(specs),
            HIGHGRADE_DYSPLASIA: has_dysplasia(pm),
            ADENOMA_COUNT: get_adenoma_count(specs),
            LARGE_ADENOMA: has_large_adenoma(pm, cm),
            ADENOMA_COUNT_ADV: adenoma_count,
            ADENOMA_STATUS_ADV: adenoma_status,
            ADENOMA_DISTAL: aden_dist_status,
            ADENOMA_DISTAL_COUNT: aden_dist_count,
            ADENOMA_PROXIMAL: aden_prox_status,
            ADENOMA_PROXIMAL_COUNT: aden_prox_count,
            ADENOMA_RECTAL: aden_rect_status,
            ADENOMA_RECTAL_COUNT: aden_rect_count,
            ADENOMA_UNKNOWN: aden_unk_status,
            ADENOMA_UNKNOWN_COUNT: aden_unk_count,
        })
    if cm:
        data.update({
            INDICATION: cm.indication,
            NUM_POLYPS: cm.num_polyps,
            BOWEL_PREP: cm.prep,
            EXTENT: cm.extent,
        })
    return data


def get_data(filetype, path, identifier=None, path_text=None, cspy_text=None, encoding='utf8',
             limit=None, count=None, truth=None, text=None, filenames=None, requires_cspy_text=False):
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
        if filenames:
            for fn in filenames:
                fp = os.path.join(path, fn)
                if not os.path.exists(fp):
                    fp = f'{fp}.{filetype}'
                yield from get_data(filetype, fp, identifier, path_text, cspy_text, truth)
        else:
            for i, fn in enumerate(os.listdir(path)):
                if count and i >= count:
                    break
                yield from get_data(filetype, os.path.join(path, fn), identifier, path_text,
                                    cspy_text, encoding, count=count, truth=truth)
    elif path and filetype == 'txt' and os.path.isfile(path):
        with open(path, encoding=encoding) as fh:
            yield os.path.basename(path), '', fh.read(), None
    else:
        if 'DataFrame' in str(type(filetype)):
            df = filetype
        elif filetype == 'csv':
            df = pd.read_csv(path, encoding=encoding)
        elif filetype == 'sas':
            df = pd.read_sas(path, encoding=encoding)
        elif filetype == 'h5':
            df = pd.read_hdf(path, 'data')
        else:
            raise ValueError(f'Unrecognized filetype: {filetype}')
        if count:
            df = df.head(count)
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


def preprocess(text, requires_cleaning=None, spell_correction=None):
    if requires_cleaning:
        text = parse_file(text)
    if spell_correction:
        pass
    return text


class DataCounter:

    def __init__(self, data=None):
        self.data = data or defaultdict(Counter)

    def __add__(self, other):
        if isinstance(other, dict):
            res = self.data.copy()
            for k, v in other.items():
                if isinstance(v, list):
                    res[k].update(v)
                else:
                    res[k][v] += 1
            return DataCounter(res)
        else:
            raise NotImplementedError(f'Cannot add {self.__class__} and {other.__class__}')

    def update(self, other, val=None):
        if isinstance(other, dict):
            for k, v in other.items():
                if isinstance(v, list):
                    self.data[k].update(v)
                else:
                    self.data[k][v] += 1
        elif isinstance(other, str):
            self.data[other][val] += 1

    def __repr__(self):
        return repr(self.data)

    def __str__(self):
        return str(self.data)

    def __iter__(self):
        for k, cnt in self.data.items():
            yield k, cnt


def process(data, truth=None, errors=None, output=None, outfile=None, preprocessing=None):
    score = defaultdict(lambda: [0, 0, 0, 0])  # TP, FP, FN, TN
    fps = defaultdict(list)
    fns = defaultdict(list)
    c = DataCounter()
    if outfile:
        fh = open(outfile, 'w', newline='')
    for i, (identifier, path_text, cspy_text, truth_values) in enumerate(get_data(**data, truth=truth)):
        if pd.isnull(path_text):
            ve = ValueError('Text cannot be missing/none')
            print(ve)
            continue
        print(f'Starting: {identifier}')
        if preprocessing:
            path_text = preprocess(path_text,
                                   **dict(preprocessing.get('all', dict()), **preprocessing.get('path', dict())))
            cspy_text = preprocess(cspy_text,
                                   **dict(preprocessing.get('all', dict()), **preprocessing.get('cspy', dict())))
        res = process_text(path_text, cspy_text)

        if outfile and i == 0:
            header = ['row', 'identifier']  # header
            if truth_values:
                outfile = csv.writer(fh)
                for label in truth_values:
                    header.append(f'{label}_true')
                    header.append(f'{label}_pred')
                outfile.writerow(header)
            else:
                header += list(res.keys())
                outfile = csv.DictWriter(fh, fieldnames=header)
                outfile.writeheader()
        row = [i, identifier]
        # collect counts
        c.update(res)
        if not res:
            c.update('failed', f'{identifier}')
        # output truth
        if truth_values:
            for label in truth_values or list():
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
        elif outfile:
            res['row'] = i
            res['identifier'] = identifier
            outfile.writerow(res)
    output_results(score, truth, fps, fns, **output if output else dict())
    print(c)
    for k, cnt in c:
        print(f'{k}\t{len(cnt)}')
        for v, count in cnt.most_common(10):
            print(f'\t{v}\t{count}')
    if outfile:
        fh.close()


def output_results(score, truth, fps, fns, max_false=5):
    for label in truth or list():
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
    preprocessing = {
        'type': 'object',
        'properties': {
            'requires_cleaning': {'type': 'boolean'},
            'spell_correction': {'type': 'string'}  # filepath
        }
    }
    schema = {
        'type': 'object',
        'properties': {
            'data': {
                'type': 'object',
                'properties': {
                    'filetype': {'type': 'string'},
                    'path': {'type': 'string'},
                    'filenames': {'type': 'array', 'items': {'type': 'string'}},
                    'identifier': {'type': 'string'},
                    'cspy_text': {'type': 'string'},
                    'requires_cspy_text': {'type': 'boolean'},
                    'path_text': {'type': 'string'},
                    'text': {'type': 'string'},  # assumed to be path_text
                    'limit': {'type': 'string'},
                    'count': {'type': 'number'},
                    'encoding': {'type': 'string'},
                }
            },
            'preprocessing': {
                'type': 'object',
                'properties': {
                    'all': preprocessing,
                    'path': preprocessing,
                    'cspy': preprocessing,
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
