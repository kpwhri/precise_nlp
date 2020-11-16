import csv
import json
import random
import sys
import warnings

try:
    import pandas as pd

    PANDAS = True
except ModuleNotFoundError:
    PANDAS = False

import os

try:
    import yaml
    YAML = True
except ModuleNotFoundError:
    YAML = False
from collections import defaultdict, Counter
from jsonschema import validate

from precise_nlp.const.cspy import INDICATION, BOWEL_PREP, EXTENT, NUM_POLYPS
from precise_nlp.const.path import HIGHGRADE_DYSPLASIA, ANY_VILLOUS, VILLOUS, TUBULAR, TUBULOVILLOUS, \
    ADENOMA_STATUS, \
    ADENOMA_COUNT, LARGE_ADENOMA, ADENOMA_COUNT_ADV, ADENOMA_STATUS_ADV, ADENOMA_DISTAL, ADENOMA_DISTAL_COUNT, \
    ADENOMA_PROXIMAL_COUNT, ADENOMA_PROXIMAL, ADENOMA_RECTAL_COUNT, ADENOMA_RECTAL, ADENOMA_UNKNOWN_COUNT, \
    ADENOMA_UNKNOWN, PROXIMAL_VILLOUS, DISTAL_VILLOUS, RECTAL_VILLOUS, UNKNOWN_VILLOUS, SIMPLE_HIGHGRADE_DYSPLASIA, \
    JAR_ADENOMA_COUNT_ADV, JAR_ADENOMA_DISTAL_COUNT, JAR_ADENOMA_PROXIMAL_COUNT, JAR_ADENOMA_RECTAL_COUNT, \
    JAR_ADENOMA_UNKNOWN_COUNT, JAR_SESSILE_SERRATED_ADENOMA_COUNT, CARCINOMA_COUNT, CARCINOMA_MAYBE_COUNT
from precise_nlp.const.enums import Location
from precise_nlp.doc_parser import parse_file
from precise_nlp.extract.algorithm import get_adenoma_status, get_adenoma_histology, get_highgrade_dysplasia, \
    get_adenoma_count, has_large_adenoma, get_adenoma_count_advanced, get_adenoma_distal, get_adenoma_proximal, \
    get_adenoma_rectal, get_adenoma_unknown, get_villous_histology, has_dysplasia, get_sessile_serrated_adenoma, \
    get_carcinomas, get_carcinomas_maybe
from precise_nlp.extract.cspy.cspy import CspyManager, FindingVersion
from precise_nlp.extract.path.path_manager import PathManager
from precise_nlp.extract.maybe_counter import MaybeCounter
from loguru import logger

ITEMS = [
    ADENOMA_STATUS,
    TUBULAR,
    TUBULOVILLOUS,
    VILLOUS,
    ANY_VILLOUS,
    PROXIMAL_VILLOUS,
    DISTAL_VILLOUS,
    RECTAL_VILLOUS,
    UNKNOWN_VILLOUS,
    SIMPLE_HIGHGRADE_DYSPLASIA,
    HIGHGRADE_DYSPLASIA,
    ADENOMA_COUNT,
    LARGE_ADENOMA,
    ADENOMA_COUNT_ADV,
    JAR_ADENOMA_COUNT_ADV,
    ADENOMA_STATUS_ADV,
    ADENOMA_DISTAL,
    ADENOMA_DISTAL_COUNT,
    JAR_ADENOMA_DISTAL_COUNT,
    ADENOMA_PROXIMAL,
    ADENOMA_PROXIMAL_COUNT,
    JAR_ADENOMA_PROXIMAL_COUNT,
    ADENOMA_RECTAL,
    ADENOMA_RECTAL_COUNT,
    JAR_ADENOMA_RECTAL_COUNT,
    ADENOMA_UNKNOWN,
    ADENOMA_UNKNOWN_COUNT,
    JAR_ADENOMA_UNKNOWN_COUNT,
    JAR_SESSILE_SERRATED_ADENOMA_COUNT,
    INDICATION,
    NUM_POLYPS,
    BOWEL_PREP,
    EXTENT,
]


def split_maybe_counters(data):
    """
    Separate maybe counters into two additional variables
        label__ge - 1 if ge, else 0
        label__num - numeric portion of number
    :param data:
    :return:
    """
    res = {}
    for k, v in data.items():
        if isinstance(v, MaybeCounter):
            if v.greater_than:
                res[f'{k}__ge'] = 1
                res[f'{k}__num'] = v.count - 1
            else:
                res[f'{k}__ge'] = 1 if v.at_least else 0
                res[f'{k}__num'] = v.count
    return res


def process_text(path_text='', cspy_text='', cspy_finding_version=FindingVersion.BROAD):
    pm = PathManager(path_text)
    cm = CspyManager(cspy_text, version=cspy_finding_version)
    data = {}
    if pm:
        specs, specs_combined, specs_dict = PathManager.parse_jars(path_text)
        tb, tbv, vl = get_adenoma_histology(pm)
        # count
        adenoma_cutoff, adenoma_status, adenoma_count = get_adenoma_count_advanced(pm)
        _, _, jar_adenoma_count = get_adenoma_count_advanced(pm, jar_count=True)
        # distal
        aden_dist_cutoff, aden_dist_status, aden_dist_count = get_adenoma_distal(pm)
        _, _, jar_ad_cnt_dist = get_adenoma_distal(pm, jar_count=True)
        # proximal
        aden_prox_cutoff, aden_prox_status, aden_prox_count = get_adenoma_proximal(pm)
        _, _, jar_ad_cnt_prox = get_adenoma_proximal(pm, jar_count=True)
        # rectal
        aden_rect_cutoff, aden_rect_status, aden_rect_count = get_adenoma_rectal(pm)
        _, _, jar_ad_cnt_rect = get_adenoma_rectal(pm, jar_count=True)
        # unk
        aden_unk_cutoff, aden_unk_status, aden_unk_count = get_adenoma_unknown(pm)
        _, _, jar_ad_cnt_unk = get_adenoma_unknown(pm, jar_count=True)
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
            LARGE_ADENOMA: has_large_adenoma(pm, cm, version=cspy_finding_version),
            ADENOMA_COUNT_ADV: adenoma_count,
            JAR_ADENOMA_COUNT_ADV: jar_adenoma_count,
            ADENOMA_STATUS_ADV: adenoma_status,
            ADENOMA_DISTAL: aden_dist_status,
            ADENOMA_DISTAL_COUNT: aden_dist_count,
            JAR_ADENOMA_DISTAL_COUNT: jar_ad_cnt_dist,
            ADENOMA_PROXIMAL: aden_prox_status,
            ADENOMA_PROXIMAL_COUNT: aden_prox_count,
            JAR_ADENOMA_PROXIMAL_COUNT: jar_ad_cnt_prox,
            ADENOMA_RECTAL: aden_rect_status,
            ADENOMA_RECTAL_COUNT: aden_rect_count,
            JAR_ADENOMA_RECTAL_COUNT: jar_ad_cnt_rect,
            ADENOMA_UNKNOWN: aden_unk_status,
            ADENOMA_UNKNOWN_COUNT: aden_unk_count,
            JAR_ADENOMA_UNKNOWN_COUNT: jar_ad_cnt_unk,
            JAR_SESSILE_SERRATED_ADENOMA_COUNT: get_sessile_serrated_adenoma(pm, jar_count=True),
            CARCINOMA_COUNT: get_carcinomas(pm, jar_count=True),
            CARCINOMA_MAYBE_COUNT: get_carcinomas_maybe(pm, jar_count=True),
        })
    if cm:
        data.update({
            INDICATION: cm.indication,
            NUM_POLYPS: cm.num_polyps,
            BOWEL_PREP: cm.prep,
            EXTENT: cm.extent,
        })
    # split maybe counters into two separate columns
    data.update(split_maybe_counters(data))
    return data


def get_file_or_empty_string(path, filename, encoding='utf8'):
    fp = os.path.join(path, filename)
    if not os.path.isfile(fp):
        return ''
    with open(fp, encoding=encoding) as fh:
        return fh.read()


def get_data(filetype, path, identifier=None, path_text=None, cspy_text=None, encoding='utf8',
             limit=None, count=None, truth=None, text=None, filenames=None, lookup_table=None,
             requires_cspy_text=False):
    """

    :param encoding:
    :param count:
    :param filenames:
    :param lookup_table:
    :param requires_cspy_text:
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
        if lookup_table:
            with open(lookup_table) as fh:
                for line in fh:
                    identifier, cspy_file, path_file = line.split(',')
                    if limit and identifier not in limit:
                        continue
                    cspy_text = get_file_or_empty_string(path, cspy_file, encoding=encoding)
                    path_text = get_file_or_empty_string(path, path_file, encoding=encoding)
                    yield identifier, path_text, cspy_text, None
        elif filenames:
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
    elif PANDAS:
        if 'DataFrame' in str(type(filetype)):
            df = filetype
        elif filetype == 'csv':
            df = pd.read_csv(path, encoding=encoding)
        elif filetype == 'tab' or filetype == 'tsv':
            df = pd.read_csv(path, sep='\t', encoding=encoding)
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
    else:
        raise ValueError(f'Unclear how to handle {filetype} with {path}; pandas installed: {PANDAS}')


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
    logger.info(f'{identifier}: {value.upper()}')
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


def process(data, truth=None, errors=None, output=None, outfile=None, preprocessing=None,
            cspy_precise_finding_version=False):
    # how to parse cspy document
    cspy_finding_version = FindingVersion.PRECISE if cspy_precise_finding_version else FindingVersion.BROAD
    score = defaultdict(lambda: [0, 0, 0, 0])  # TP, FP, FN, TN
    fps = defaultdict(list)
    fns = defaultdict(list)
    c = DataCounter()
    if outfile:
        fh = open(outfile, 'w', newline='')
    for i, (identifier, path_text, cspy_text, truth_values) in enumerate(get_data(**data, truth=truth)):
        if PANDAS and pd.isnull(path_text) or path_text is None:
            ve = ValueError('Text cannot be missing/none')
            print(ve)
            continue
        logger.info(f'Starting: {identifier}')
        if preprocessing:
            path_text = preprocess(path_text,
                                   **dict(preprocessing.get('all', dict()), **preprocessing.get('path', dict())))
            cspy_text = preprocess(cspy_text,
                                   **dict(preprocessing.get('all', dict()), **preprocessing.get('cspy', dict())))
        res = process_text(path_text, cspy_text, cspy_finding_version=cspy_finding_version)

        if outfile and i == 0:
            header = ['row', 'identifier']  # header
            if truth_values:
                # noinspection PyUnboundLocalVariable
                outfile = csv.writer(fh)
                for label in truth_values:
                    header.append(f'{label}_true')
                    header.append(f'{label}_pred')
                outfile.writerow(header)
            else:
                header += list(res.keys())
                outfile = csv.DictWriter(fh, fieldnames=header + [item for item in ITEMS if item not in set(header)])
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
                    logger.info(f'{identifier}: TN')
                    score[label][3] += 1
                elif res[label] == truth_item:
                    logger.info(f'{identifier}: TP')
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
    logger.info(c)
    for k, cnt in c:
        logger.info(f'{k}\t{len(cnt)}')
        for v, count in cnt.most_common(10):
            logger.info(f'\t{v}\t{count}')
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
                    'limit': {'type': 'array', 'items': {'type': 'string'}},
                    'count': {'type': 'number'},
                    'encoding': {'type': 'string'},
                    'lookup_table': {'type': 'string'},  # identifier,cspy_file,path_file
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
            'cspy_precise_finding_version': {'type': 'boolean'}
        }
    }
    conf_fp = sys.argv[1]
    with open(conf_fp) as conf:
        if conf_fp.endswith('json'):
            config = json.load(conf)
        elif conf_fp.endswith('yaml'):
            if not YAML:
                raise ValueError('Yaml package not available. Please install.')
            config = yaml.load(conf)
        else:
            raise ValueError(f'Unrecognized config file type "{os.path.splitext(conf_fp)[-1]}". Expected "yaml" or "json".')
    validate(config, schema)
    process(**config)


if __name__ == '__main__':
    process_config()
