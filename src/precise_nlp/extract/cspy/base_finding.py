import re

from loguru import logger

from precise_nlp.const import patterns
from precise_nlp.extract.utils import depth_to_location, StandardTerminology, NumberConvert


class BaseFinding:

    def __init__(self, location=None, count=1, removal=None,
                 size=None, source=None):
        """

        :param location:
        :param count: default to 1
        :param removal:
        :param size: in mm
        """
        if location:
            self._locations = [location]
        else:
            self._locations = []
        self._count = count
        self.removal = removal
        self.size = size
        self.source = None

    @property
    def locations(self):
        return tuple(self._locations)

    def __repr__(self):
        removed = 'removed' if self.removal else ''
        return f'<{self.count}{removed}@{",".join(self.locations)}:{self.size}>'

    def __str__(self):
        return repr(self)

    @property
    def count(self):
        return self._count if self._count else 1

    def add_locations(self, *locations):
        self._locations.extend(
            StandardTerminology.standardize_locations(locations)
        )

    def add_location(self, location):
        loc = StandardTerminology.standardize_location(location)
        self._locations.append(loc)

    def extract_depth(self, pat, value):
        new_value = []
        end = 0
        for m in pat.finditer(value):
            if 'size' in value[m.end():m.end() + 15]:
                continue
            self._locations += depth_to_location(float(m.group(1)))
            new_value.append(value[end:m.start()])
            end = m.end()
        new_value.append(value[end:])
        return ' '.join(new_value)

    def extract_size(self, pat, value):
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

        for m in pat.finditer(value):
            size = max(get_size(m.group(n)) for n in ('n1', 'n2'))
            if m.group('m')[-2] == 'c':  # mm
                size *= 10  # convert to mm
            if size > 100:
                continue
            if not self.size or size > self.size:  # get largest size only
                self.size = size
            new_value.append(value[end:m.start()])
            end = m.end()
        new_value.append(value[end:])
        return ' '.join(new_value)

    @classmethod
    def parse_finding(cls, s, prev_locations=None, source=None):
        key = None
        value = None
        if '-' in s:
            key, value = s.lower().split('-', maxsplit=1)
        if '—' in s:
            key, value = s.lower().split('—', maxsplit=1)
        elif ':' in s:
            key, value = s.lower().split(':', maxsplit=1)
        if not key or len(key) > 40:
            key = None
            value = s.lower()
        f = cls(source=source)
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
                f._locations.append(location)
            elif not key and loc_pat.search(value):
                logger.warning(f'Possible unrecognized finding separator in "{s}"')
                f._locations.append(location)
        # update locations if none found
        if prev_locations and not f._locations:
            f._locations = prev_locations
        else:
            f._locations = StandardTerminology.standardize_locations(f._locations)
        # there should only be one
        f._count = max(NumberConvert.contains(value, ['polyp', 'polyps'], 3,
                                              split_on_non_word=True) + [0])
        f.removal = 'remove' in value or 'retriev' in value
        return f

    def is_standalone(self, prev_locations):
        """Need more than just removal and prev_locations"""
        if self._locations != prev_locations:
            return True
        elif self.size:
            return True
        elif self._count:
            return True
        return False
