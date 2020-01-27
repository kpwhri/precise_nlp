import enum
import re
from collections import namedtuple
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple

from loguru import logger

from precise_nlp.const import patterns
from precise_nlp.extract.cspy.base_finding import BaseFinding
from precise_nlp.extract.cspy.single_finding import SingleFinding
from precise_nlp.extract.utils import StandardTerminology, NumberConvert, depth_to_location


class FindingType(enum.Enum):
    NAIVE_FINDING = 1
    SINGLE_FINDING = 2


class FindingState(enum.Enum):
    START = 0
    NONE = 1
    COUNT = 2
    SIZE = 3
    NO_SIZE = 4
    SIZE_NO_DEPTH = 5
    NO_SIZE_DEPTH = 6
    NO_SIZE_NO_DEPTH = 7
    DONE = 8
    LOCATION = 9
    NO_SIZES = 10
    REMOVED = 11

    # def __init__(self, name, accepting=False):


@dataclass
class Finding:
    count: int = 0
    size: int = 0
    locations: Tuple[str] = field(default_factory=tuple)
    removal: bool = False
    depth: int = 0


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
        accept_state = (None, None, None)
        self.TRANSITIONS = {
            # current state -> func, next_if_true, next_if_false
            FindingState.START: (self.get_count, FindingState.COUNT, FindingState.LOCATION),
            FindingState.COUNT: (self.extract_size1, FindingState.SIZE, FindingState.NO_SIZE),
            FindingState.SIZE: (self.extract_depth1, FindingState.REMOVED, FindingState.SIZE_NO_DEPTH),
            FindingState.SIZE_NO_DEPTH: (self.extract_depth2, FindingState.REMOVED, FindingState.LOCATION),
            FindingState.NO_SIZE: (self.extract_depth1, FindingState.NO_SIZE_DEPTH, FindingState.NO_SIZE_NO_DEPTH),
            FindingState.NO_SIZE_DEPTH: (self.extract_size2, FindingState.REMOVED, FindingState.REMOVED),
            FindingState.NO_SIZE_NO_DEPTH: (self.extract_size2, FindingState.SIZE_NO_DEPTH, FindingState.NO_SIZES),
            FindingState.NO_SIZES: (self.extract_depth2, FindingState.REMOVED, FindingState.LOCATION),
            FindingState.LOCATION: (self.extract_location, FindingState.REMOVED, FindingState.REMOVED),
            FindingState.REMOVED: (self.was_removed, FindingState.DONE, FindingState.DONE),  # TODO: not included
            FindingState.DONE: accept_state,
        }

    def split_key_text(self, text, *, splitters='-—:', max_length=40):
        text = text.lower()
        for spl in splitters:
            if spl in text:
                key, val = text.split(spl, maxsplit=1)
                if len(key) <= max_length:
                    return key, val
        return None, text

    def fsm(self, text):
        key, text = self.split_key_text(text)
        finding = Finding()
        state = FindingState.START
        while True:
            func, true_state, false_state = self.TRANSITIONS[state]
            if func is None:
                break
            indicator, text = func(finding, text, key=key)
            state = true_state if indicator else false_state
        self._findings.append(finding)
        return finding

    def was_removed(self, finding, text, **kwargs):
        finding.removal = 'remove' in text or 'retriev' in text
        return finding.removal, text

    def extract_location(self, finding, text, key, **kwargs):
        locations = []
        for location in StandardTerminology.LOCATIONS:
            loc_pat = re.compile(fr'\b{location}\b', re.IGNORECASE)
            if key and loc_pat.search(key):
                locations.append(location)
            elif not key and loc_pat.search(text):
                logger.warning(f'Possible unrecognized finding separator in "{text}"')
                locations.append(location)
        if locations:
            finding.locations = tuple(locations)
        return len(locations) > 0, text

    def _extract_size(self, finding, pat, value):
        new_value = []
        end = 0

        def get_size(s):
            if not s:
                return 0
            if s[0] == '<':
                return float(s[1:]) - 0.1
            elif s[0] == '>':
                return float(s[1:]) + 0.1
            else:
                return float(s)

        size = 0
        for m in pat.finditer(value):
            curr_size = max(get_size(m.group(n)) for n in ('n1', 'n2'))
            if m.group('m')[-2] == 'c':  # mm
                curr_size *= 10  # convert to mm
            if curr_size > 100:
                continue
            if curr_size > size:  # get largest size only
                size = curr_size
            new_value.append(value[end:m.start()])
            end = m.end()
        new_value.append(value[end:])
        if size:
            finding.size = size
        return bool(size), ' '.join(new_value)

    def get_count(self, finding, text, **kwargs):
        # there should only be one
        lst = [0]
        if 'polyps' in text:
            lst.append(2)
        elif 'polyp' in text:
            lst.append(1)
        else:
            return False, text
        count = max(NumberConvert.contains(text, ('polyp', 'polyps'), 3,
                                           split_on_non_word=True) + lst)
        finding.count = count
        return count > 0, text

    def _extract_depth(self, finding, pat, value):
        new_value = []
        end = 0
        locations = []
        for m in pat.finditer(value):
            if 'size' in value[m.end():m.end() + 15]:
                continue
            locations += depth_to_location(float(m.group(1)))
            new_value.append(value[end:m.start()])
            end = m.end()
        new_value.append(value[end:])
        if locations:
            finding.locations = locations
        return len(locations) > 0, ' '.join(new_value)

    def extract_depth1(self, finding, text, **kwargs):
        return self._extract_depth(finding, patterns.AT_DEPTH_PATTERN, text)

    def extract_depth2(self, finding, text, **kwargs):
        return self._extract_depth(finding, patterns.CM_DEPTH_PATTERN, text)

    def extract_size1(self, finding, text, **kwargs):
        return self._extract_size(finding, patterns.IN_SIZE_PATTERN, text)

    def extract_size2(self, finding, text, **kwargs):
        return self._extract_size(finding, patterns.SIZE_PATTERN, text)

    def get_findings(self) -> Iterable[BaseFinding]:
        yield from self._findings
