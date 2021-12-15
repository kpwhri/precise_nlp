from regexify.pattern import Pattern

from precise_nlp.extract.cspy.finding_builder import Finding, FindingSource

colon = r'(colon|flexure)'
_size = lambda x='': r'(?P<size{}>\d+)'.format(x)
_measure = lambda x='': r'(?P<measure{}>[cm]m)'.format(x)
_location = lambda x='': r'(?P<location{}>\w+)'.format(x)
_location_rectum = r'(?P<location>rect\w+)'
_word = lambda x='3': r'(\w+\W+){{0,{}}}'.format(x)

FINDING_PATTERNS = {
    'POLYP_SIZE_IN_LOCATION': Pattern(
        rf'polyp {_size()} {_measure()} in the {_location()} {colon}'
    ),
    'POLYP_SIZE_3W_LOCATION': Pattern(
        rf'polyp {_size()} {_measure()} {_word(3)}{_location()} {colon}'
    ),
    'POLYP_SIZE_3W_RECTUM': Pattern(
        rf'polyp {_size()} {_measure()} {_word(3)}{_location_rectum}'
    ),
    'POLYPS_SIZE_3W_LOCATION': Pattern(
        rf'polyps {_size(1)} {_measure(1)}? (?:to|-)'
        rf' {_size(2)} {_measure(2)} {_word(3)}{_location()} {colon}'
    ),
    'POLYPS_SIZE_3W_LOCATIONS': Pattern(
        rf'polyps {_size(1)} {_measure(1)}? (?:to|-)'
        rf' {_size(2)} {_measure(2)} {_word(3)}{_location()} {colon}'
    ),
}


def get_size(size, measure, measure2=None):
    size = int(size)
    if measure and measure.lower().strip() == 'cm':
        size *= 10
    elif not measure and measure2 and measure2.lower().strip() == 'cm':
        size *= 10
    return size


def get_locations(*locations):
    return tuple(locations)


def apply_finding_patterns(text, source: FindingSource = None) -> list[Finding]:
    for name, pat in FINDING_PATTERNS.items():
        if m := pat.matches(text):
            d = m.groupdict()
            print(name, d)
            match sorted(list(d.keys())):
                case ['location', 'measure', 'size']:
                    yield Finding(
                        count=1,
                        sizes=(get_size(d['size'], d['measure']),),
                        locations=get_locations(d['location']),
                        source=source,
                    )
                case ['location', 'measure1', 'measure2', 'size1', 'size2']:
                    yield Finding(
                        count=2,
                        sizes=(
                            get_size(d['size1'], d['measure1'], d['measure2']),
                            get_size(d['size2'], d['measure2'], d['measure1']),
                        ),
                        locations=get_locations(d['location'], ),
                        source=source,
                    )
                case other:
                    raise ValueError(f'Unrecognized: {other}')
            break
