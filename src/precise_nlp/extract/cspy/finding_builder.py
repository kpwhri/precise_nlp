import enum
import re
from typing import Iterable

from loguru import logger

from precise_nlp.const import patterns
from precise_nlp.extract.cspy.base_finding import BaseFinding
from precise_nlp.extract.cspy.single_finding import SingleFinding
from precise_nlp.extract.utils import StandardTerminology, NumberConvert


class FindingType(enum.Enum):
    NAIVE_FINDING = 1
    SINGLE_FINDING = 2


class FindingBuilder:

    def __init__(self, version=FindingType.SINGLE_FINDING):
        self._findings = []
        self._locations = []
        self._version = version
        self._current = []
        if version == FindingType.SINGLE_FINDING:
            self.cls = SingleFinding
        else:
            raise ValueError(f'Unknown Finding class: {version}')

    def extract_findings(self, text, source=None):
        key = None
        value = None
        if '-' in text:
            key, value = text.lower().split('-', maxsplit=1)
        if '—' in text:
            key, value = text.lower().split('—', maxsplit=1)
        elif ':' in text:
            key, value = text.lower().split(':', maxsplit=1)
        if not key or len(key) > 40:
            key = None
            value = text.lower()
        f = self.cls(source=source)
        # in size pattern
        value = f.extract_size(patterns.IN_SIZE_PATTERN, value)
        # look for location as an "at 10cm" expression
        value = f.extract_depth(patterns.AT_DEPTH_PATTERN, value)
        if not f.size:
            value = f.extract_size(patterns.SIZE_PATTERN, value)
        if not f.locations:
            # without at, require 2 digits and "CM"
            value = f.extract_depth(patterns.CM_DEPTH_PATTERN, value)
        # spelled-out locations
        for location in StandardTerminology.LOCATIONS:
            loc_pat = re.compile(fr'\b{location}\b', re.IGNORECASE)
            if key and loc_pat.search(key):
                f.add_location(location)
            elif not key and loc_pat.search(value):
                logger.warning(f'Possible unrecognized finding separator in "{text}"')
                f.add_location(location)
        # update locations if none found
        if self._locations and not f.locations:
            f.add_locations(self._locations)
        # there should only be one
        count = max(NumberConvert.contains(value, ['polyp', 'polyps'], 3,
                                           split_on_non_word=True) + [0])
        if count:  # this resets everything

        f.removal = 'remove' in value or 'retriev' in value
        return f

    def get_findings(self) -> Iterable[BaseFinding]:
        yield from self._findings
