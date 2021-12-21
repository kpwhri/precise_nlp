import re

from regexify.pattern import Pattern
from loguru import logger

from precise_nlp.extract.cspy.finding_builder import Finding, FindingSource
from precise_nlp.extract.cspy.polyps import POLYP_IDENTIFIERS, POLYP_IDENTIFIERS_PATTERN
from precise_nlp.extract.utils import NumberConvert, StandardTerminology

colon = r'(colon|flexure)'
_to = r'(?:to|-|and)'
_kind = r'(?:(?:sessile|pedunc\w+|flat) )'
_size = lambda x='': r'(?P<size{}>\d+\.?\d*|\d*\.\d+)'.format(x)
_measure = lambda x='': r'(?P<measure{}>[cm]m)'.format(x)
_polyp_qual = lambda x='': r'(?P<polyp_qual{}>{})(?:ly)? (?:sized?)?'.format(x, POLYP_IDENTIFIERS_PATTERN)
_size_qual = lambda x='': f'(?:{_size(x)} {_measure(x)}?|{_polyp_qual(x)})'
_size_to_size_qual = lambda x='': f'{_size_qual(x or 1)} {_to} {_size_qual(x + 1 if x else 2)}'
_location = lambda x='': r'(?P<location{}>\w+)'.format(x)
_location_at = lambda x='': r'(?:at|@)? (?P<location_at{}>\d+) cm'.format(x)
_location_terminal = lambda x='': r'(?P<location_rectum{}>(?:rect|cec)\w+)'.format(x)
_location_or_rectum = lambda x='': f'(?:{_location(x)} {colon}|{_location_terminal(x)}|{colon}? {_location_at(x)})'
_location_all = lambda x='': r'(?P<location{}>{})(?: {})?'.format(x, StandardTerminology.LOCATION_PATTERN, colon)
_word = lambda x='3': r'(\w+\W+){{0,{}}}'.format(x)
_word_space = lambda x='3': r'(\w+[\s\.]+){{0,{}}}'.format(x)
_count = lambda x='': r'(?P<count{}>{})'.format(x, NumberConvert.NUMBER_PATTERN)

IN_LOCATION_FINDING_PATTERNS = {  # patterns that assume we are in a location section (i.e., we know location)
    f'NUM_SIZES_POLYP': Pattern(
        rf'{_count()} {_size_to_size_qual()} {_kind}?polyp'
    ),
    f'NUM_SIZE_POLYP': Pattern(
        rf'{_count()} {_size_qual()} {_kind}?polyp'
    ),
    f'SIZES_POLYP': Pattern(
        rf'{_polyp_qual(9)} {_size_to_size_qual()} polyp'
    ),
    f'SIZE_POLYP': Pattern(
        rf'{_polyp_qual(9)} {_size_qual()} polyp'
    ),
    f'NUM_POLYP_SIZE': Pattern(
        rf'{_count()} {_kind}? polyps? the polyps? (was|were) {_size_qual()}'
    )
}

FINDING_PATTERNS = {  # for any findings, but particularly for 'Findings:' section
    'POLYP_SIZE_IN_LOCATION': Pattern(
        rf'polyp {_size_qual()} in the {_location_or_rectum()}'
    ),
    'POLYP_SIZE_3W_LOCATION': Pattern(
        rf'polyp {_size_qual()} {_word(3)}{_location_or_rectum()}'
    ),
    'POLYPS_SIZE_3W_LOCATIONS': Pattern(
        rf'polyps {_size_to_size_qual()} {_word(3)}'
        rf'{_location_or_rectum(1)} {_word(3)}{_location_or_rectum(2)}'
    ),
    'POLYPS_SIZE_3W_LOCATION': Pattern(
        rf'polyps {_size_qual(1)} {_to}'
        rf' {_size_qual(2)} {_word(3)}{_location_or_rectum()}'
    ),
    f'NUM_SIZE_LOCATION': Pattern(
        rf'{_count()} {_size_qual()} polyps? {_word(3)}{_location_or_rectum()}'
    ),
    f'NUM_SIZES_LOCATION': Pattern(
        rf'{_count()} {_size_qual(1)} {_to} {_size_qual(2)} polyps? {_word(3)}{_location_or_rectum()}'
    ),
    f'POLYP_LOCATION_SIZE': Pattern(
        rf'polyp location {_location_all()} size {_size_qual()}'
    ),
    f'LOCATION_NUM_SIZE_POLYP': Pattern(
        rf'{_location_all()} {_count()} {_size_qual()} {_kind}?polyp'
    ),
    f'LOCATION_NUM_SIZES_POLYP': Pattern(
        rf'{_location_all()} {_count()} {_size_to_size_qual()} {_kind}?polyp'
    ),
    f'LOCATION_SIZE_POLYP': Pattern(
        rf'{_location_all()} {_polyp_qual(9)} {_size_qual()} polyp'
    ),
    f'LOCATION_SIZES_POLYP': Pattern(
        rf'{_location_all()} {_polyp_qual(9)} {_size_to_size_qual()} polyp'
    ),
    f'LOCATION_NUM_POLYP_SIZE': Pattern(
        rf'{_location_all()} {_word_space(3)} {_count()} {_kind}? polyps? '
        rf'the polyps? (was|were) {_size_qual()}'
    )
}

MISSING_PATTERNS = {  # these patterns might suggest something is missing in the above set
    f'LOCATION_NUM_SIZE_POLYP_without_ending': Pattern(
        rf'{_location_all()} {_count()} {_size_qual()}'
    )
}


def get_count(count):
    return NumberConvert.convert(count)


def regex_strip(term, remove=r'\W'):
    for i, letter in enumerate(term):
        if not re.match(remove, letter):
            term = term[i:]
            break
    for i, letter, in enumerate(reversed(term)):
        if not re.match(remove, letter):
            if i > 0:
                term = term[:-i]
            break
    return term


def get_size(size, measure, measure2=None):
    size = regex_strip(size)
    if size in POLYP_IDENTIFIERS:
        return POLYP_IDENTIFIERS[size]
    size = float(size)
    if measure and measure.lower().strip() == 'cm':
        size *= 10
    elif not measure and measure2 and measure2.lower().strip() == 'cm':
        size *= 10
    return size


def get_locations_from_groupdict(d):
    return get_locations(*(v for k, v in d.items() if k.startswith('location')))


def get_locations(*locations):
    return tuple(loc for location in locations for loc in StandardTerminology.convert_location(location) if location)


def remove_finding_patterns(text):
    for pat in FINDING_PATTERNS.values():
        text = pat.sub(' ', text)
    return text.strip()


def apply_finding_patterns(text, source: FindingSource = None, *, debug=False) -> list[Finding]:
    found = False
    for name, pat in FINDING_PATTERNS.items():
        for m in pat.finditer(text):
            d = m.groupdict()
            found = True
            logger.debug(f'Found pattern {name}: {d}')
            logger.debug(f'Matching case: {sorted(d.keys())}')
            match sorted(list(d.keys())):
                case ['location', 'location_at', 'location_rectum', 'measure', 'polyp_qual', 'size']:
                    yield Finding(
                        count=get_count(d.get('count', 1)),
                        sizes=(get_size(d['size'] or d['polyp_qual'], d['measure']),),
                        locations=get_locations_from_groupdict(d),
                        source=source,
                    )
                case ['count', 'location', 'measure', 'polyp_qual', 'size']:
                    yield Finding(
                        count=get_count(d['count']),
                        sizes=(get_size(d['size'] or d['polyp_qual'], d['measure']),),
                        locations=get_locations_from_groupdict(d),
                        source=source,
                    )
                case (
                ['location', 'location_at', 'location_rectum', 'measure1', 'measure2',
                 'polyp_qual1', 'polyp_qual2', 'size1', 'size2'] |
                ['count', 'location', 'measure1', 'measure2', 'polyp_qual1', 'polyp_qual2', 'size1', 'size2'] |
                ['location1', 'location2', 'location_at1', 'location_at2', 'location_rectum1', 'location_rectum2',
                 'measure1', 'measure2', 'polyp_qual1', 'polyp_qual2', 'size1', 'size2']
                ):
                    yield Finding(
                        count=get_count(d.get('count', 2)),
                        sizes=(
                            get_size(d['size1'] or d['polyp_qual1'], d['measure1'], d['measure2']),
                            get_size(d['size2'] or d['polyp_qual2'], d['measure2'], d['measure1']),
                        ),
                        locations=get_locations_from_groupdict(d),
                        source=source,
                    )
                case ['count', 'location', 'location_at', 'location_rectum', 'measure', 'polyp_qual', 'size']:
                    yield Finding(
                        count=get_count(d['count']),
                        sizes=(
                            get_size(d['size'] or d['polyp_qual'], d['measure']),
                        ),
                        locations=get_locations_from_groupdict(d),
                        source=source,
                    )
                case ['count', 'location', 'location_at', 'location_rectum', 'measure1', 'measure2',
                      'polyp_qual1', 'polyp_qual2', 'size1', 'size2']:
                    yield Finding(
                        count=get_count(d['count']),
                        sizes=(
                            get_size(d['size1'] or d['polyp_qual1'], d['measure1'], d['measure2']),
                            get_size(d['size2'] or d['polyp_qual2'], d['measure2'], d['measure1']),
                        ),
                        locations=get_locations_from_groupdict(d),
                        source=source,
                    )
                case (['location', 'measure', 'polyp_qual', 'size']
                      | ['location', 'measure', 'polyp_qual', 'polyp_qual9', 'size']):
                    yield Finding(
                        count=get_count(d.get('count', 1)),
                        sizes=(
                            get_size(d['size'] or d['polyp_qual'], d['measure']),
                        ),
                        locations=get_locations_from_groupdict(d),
                        source=source,
                    )
                case other:
                    raise ValueError(f'Unrecognized for {name}: {other}')
        text = pat.sub(' ', text).strip()

    if not found and debug:
        for name, pat in MISSING_PATTERNS.items():
            if m := pat.matches(text):
                logger.info(f'Missing pattern: {name} in {text[max(0, m.start() - 10): m.end() + 20]}')


def apply_finding_patterns_to_location(text, location, source: FindingSource = None, *, debug=False) -> list[Finding]:
    found = False
    for name, pat in IN_LOCATION_FINDING_PATTERNS.items():
        for m in pat.finditer(text):
            found = True
            d = m.groupdict()
            logger.debug(f'Found pattern {name}: {d}')
            logger.debug(f'Matching case: {sorted(d.keys())}')
            match sorted(list(d.keys())):
                case ['measure', 'polyp_qual', 'size']:
                    yield Finding(
                        count=get_count(d.get('count', 1)),
                        sizes=(get_size(d['size'] or d['polyp_qual'], d['measure']),),
                        locations=location,
                        source=source,
                    )
                case ['count', 'measure', 'polyp_qual', 'size']:
                    yield Finding(
                        count=get_count(d['count']),
                        sizes=(get_size(d['size'] or d['polyp_qual'], d['measure']),),
                        locations=location,
                        source=source,
                    )
                case (
                ['measure1', 'measure2', 'polyp_qual1', 'polyp_qual2', 'size1', 'size2'] |
                ['count', 'measure1', 'measure2', 'polyp_qual1', 'polyp_qual2', 'size1', 'size2'] |
                ['measure1', 'measure2', 'polyp_qual1', 'polyp_qual2', 'size1', 'size2']
                ):
                    yield Finding(
                        count=get_count(d.get('count', 2)),
                        sizes=(
                            get_size(d['size1'] or d['polyp_qual1'], d['measure1'], d['measure2']),
                            get_size(d['size2'] or d['polyp_qual2'], d['measure2'], d['measure1']),
                        ),
                        locations=location,
                        source=source,
                    )
                case ['count', 'measure1', 'measure2', 'polyp_qual1', 'polyp_qual2', 'size1', 'size2']:
                    yield Finding(
                        count=get_count(d['count']),
                        sizes=(
                            get_size(d['size1'] or d['polyp_qual1'], d['measure1'], d['measure2']),
                            get_size(d['size2'] or d['polyp_qual2'], d['measure2'], d['measure1']),
                        ),
                        locations=location,
                        source=source,
                    )
                case (['measure', 'polyp_qual', 'size']
                      | ['measure', 'polyp_qual', 'polyp_qual9', 'size']):
                    yield Finding(
                        count=get_count(d.get('count', 1)),
                        sizes=(
                            get_size(d['size'] or d['polyp_qual'], d['measure']),
                        ),
                        locations=location,
                        source=source,
                    )
                case other:
                    raise ValueError(f'Unrecognized for {name}: {other}')
        if found:
            break
