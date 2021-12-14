from typing import List

from regexify.pattern import Pattern

from precise_nlp.extract.cspy.finding_builder import Finding

FINDING_PATTERNS = {
    'POLYP_SIZE_IN_LOCATION': Pattern(r'polyp (?P<size>\d+) mm in the (?P<location>\w+) colon'),
    'POLYP_SIZE_3W_LOCATION': Pattern(r'polyp (?P<size>\d+) mm (\w+ ){0,3}(?P<location>\w+) colon'),
}


def apply_finding_patterns(text) -> List[Finding]:
    for name, pat in FINDING_PATTERNS.items():
        if m := pat.matches(text):
            yield Finding(
                count=1,
                sizes=(int(m.group('size')),),
                locations=(m.group('location'),),
            )
