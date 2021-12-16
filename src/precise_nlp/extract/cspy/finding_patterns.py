import re

from regexify.pattern import Pattern

from precise_nlp.extract.cspy.finding_builder import Finding, FindingSource
from precise_nlp.extract.cspy.polyps import POLYP_IDENTIFIERS, POLYP_IDENTIFIERS_PATTERN
from precise_nlp.extract.utils import NumberConvert, StandardTerminology

colon = r'(colon|flexure)'
_to = r'(?:to|-)'
_size = lambda x='': r'(?P<size{}>\d+)'.format(x)
_measure = lambda x='': r'(?P<measure{}>[cm]m)'.format(x)
_polyp_qual = lambda x='': r'(?P<polyp_qual{}>{})(?:ly)? (?:sized?)?'.format(x, POLYP_IDENTIFIERS_PATTERN)
_size_qual = lambda x='': f'(?:{_size(x)} {_measure(x)}?|{_polyp_qual(x)})'
_location = lambda x='': r'(?P<location{}>\w+)'.format(x)
_location_terminal = lambda x='': r'(?P<location_rectum{}>(?:rect|cec)\w+)'.format(x)
_location_or_rectum = lambda x='': f'(?:{_location(x)} {colon}|{_location_terminal(x)})'
_location_all = lambda x='': r'(?P<location{}>{})( {})?'.format(x, StandardTerminology.LOCATION_PATTERN, colon)
_word = lambda x='3': r'(\w+\W+){{0,{}}}'.format(x)
_count = lambda x='': r'(?P<count{}>{})'.format(x, NumberConvert.NUMBER_PATTERN)

FINDING_PATTERNS = {
    'POLYP_SIZE_IN_LOCATION': Pattern(
        rf'polyp {_size_qual()} in the {_location_or_rectum()}'
    ),
    'POLYP_SIZE_3W_LOCATION': Pattern(
        rf'polyp {_size_qual()} {_word(3)}{_location_or_rectum()}'
    ),
    'POLYPS_SIZE_3W_LOCATIONS': Pattern(
        rf'polyps {_size_qual(1)} {_to}'
        rf' {_size_qual(2)} {_word(3)}'
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
    )
}


def get_count(count):
    return NumberConvert.convert(count)


def get_size(size, measure, measure2=None):
    size = re.sub(r'\W+', ' ', size)
    if size in POLYP_IDENTIFIERS:
        return POLYP_IDENTIFIERS[size]
    size = int(size)
    if measure and measure.lower().strip() == 'cm':
        size *= 10
    elif not measure and measure2 and measure2.lower().strip() == 'cm':
        size *= 10
    return size


def get_locations_from_groupdict(d):
    return get_locations(*(v for k, v in d.items() if k.startswith('location')))


def get_locations(*locations):
    return tuple(loc for location in locations for loc in StandardTerminology.convert_location(location) if location)


def apply_finding_patterns(text, source: FindingSource = None) -> list[Finding]:
    for name, pat in FINDING_PATTERNS.items():
        if m := pat.matches(text):
            d = m.groupdict()
            print(name, d)
            match sorted(list(d.keys())):
                case ['location', 'location_rectum', 'measure', 'polyp_qual', 'size']:
                    yield Finding(
                        count=1,
                        sizes=(get_size(d['size'], d['measure']),),
                        locations=get_locations_from_groupdict(d),
                        source=source,
                    )
                case ['location', 'location_rectum', 'measure1', 'measure2',
                      'polyp_qual1', 'polyp_qual2', 'size1', 'size2']:
                    yield Finding(
                        count=2,
                        sizes=(
                            get_size(d['size1'] or d['polyp_qual1'], d['measure1'], d['measure2']),
                            get_size(d['size2'] or d['polyp_qual2'], d['measure2'], d['measure1']),
                        ),
                        locations=get_locations_from_groupdict(d),
                        source=source,
                    )
                case ['location1', 'location2', 'location_rectum1', 'location_rectum2',
                      'measure1', 'measure2', 'polyp_qual1', 'polyp_qual2', 'size1', 'size2']:
                    yield Finding(
                        count=2,
                        sizes=(
                            get_size(d['size1'] or d['polyp_qual1'], d['measure1'], d['measure2']),
                            get_size(d['size2'] or d['polyp_qual2'], d['measure2'], d['measure1']),
                        ),
                        locations=get_locations_from_groupdict(d),
                        source=source,
                    )
                case ['count', 'location', 'location_rectum', 'measure', 'polyp_qual', 'size']:
                    yield Finding(
                        count=get_count(d['count']),
                        sizes=(
                            get_size(d['size'] or d['polyp_qual'], d['measure']),
                        ),
                        locations=get_locations_from_groupdict(d),
                        source=source,
                    )
                case ['count', 'location', 'location_rectum', 'measure1', 'measure2',
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
                case ['location', 'measure', 'polyp_qual', 'size']:
                    yield Finding(
                        count=1,
                        sizes=(
                            get_size(d['size'] or d['polyp_qual'], d['measure']),
                        ),
                        locations=get_locations_from_groupdict(d),
                        source=source,
                    )
                case other:
                    raise ValueError(f'Unrecognized: {other}')
            break
