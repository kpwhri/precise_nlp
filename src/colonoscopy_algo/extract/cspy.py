import collections
import logging
import re

from colonoscopy_algo.const import patterns
from colonoscopy_algo.const.patterns import INDICATION_DIAGNOSTIC, INDICATION_SURVEILLANCE, INDICATION_SCREENING, \
    PROCEDURE_EXTENT, COLON_PREP_PRE, COLON_PREP_POST
from colonoscopy_algo.extract.utils import NumberConvert, depth_to_location, StandardTerminology, Indication, Extent, \
    ColonPrep


class Finding:

    def __init__(self, location=None, count=1, removal=None, size=None, source=None):
        """

        :param location:
        :param count: default to 1
        :param removal:
        :param size: in mm
        """
        if location:
            self.locations = [location]
        else:
            self.locations = []
        self.count = count
        self.removal = removal
        self.size = size
        self.source = None

    def __repr__(self):
        return f'<{self.count}{{}}@{",".join(self.locations)}:{self.size}>'.format('removed' if self.removal else '')

    def __str__(self):
        return repr(self)

    def is_compatible(self, f):
        if not isinstance(f, Finding):
            raise ValueError('Can only compare findings')
        if self.source == f.source:
            if self.count != f.count:  # counts must be the same
                return False
            elif set(self.locations) != set(f.locations):
                return False
            elif self.size and f.size:
                return False
        else:  # sources not equal
            if self.count and f.count and self.count != f.count:
                return False
            elif self.removal and f.removal and self.removal != f.removal:
                return False
            elif self.locations and f.locations and set(self.locations) | set(f.locations):
                return False
            elif self.size and f.size and self.size != f.size:
                return False
        return True

    def merge(self, f):
        if not isinstance(f, Finding):
            raise ValueError('Can only merge findings')
        self.count = max(self.count, f.count)
        self.removal = self.removal or f.removal
        self.locations += f.locations
        if self.size and f.size:
            self.size = max(self.size, f.size)
        elif f.size:
            self.size = f.size

    @staticmethod
    def parse_finding(s, prev_locations=None, source=None):
        key = None
        value = None
        if '-' in s:
            key, value = s.lower().split('-', maxsplit=1)
        elif ':' in s:
            key, value = s.lower().split(':', maxsplit=1)
        if not key or len(key) > 40:
            key = None
            value = s.lower()
        f = Finding(source=source)
        # look for location as an "at 10cm" expression
        new_value = []
        end = 0
        for m in patterns.AT_DEPTH_PATTERN.finditer(value):
            f.locations += depth_to_location(float(m.group(1)))
            new_value.append(value[end:m.start()])
            end = m.end()
        new_value.append(value[end:])
        value = ' '.join(new_value)
        # without at, require 2 digits and "CM"
        new_value = []
        end = 0
        for m in patterns.CM_DEPTH_PATTERN.finditer(value):
            f.locations += depth_to_location(float(m.group(1)))
            new_value.append(value[end:m.start()])
            end = m.end()
        new_value.append(value[end:])
        value = ' '.join(new_value)
        for location in StandardTerminology.LOCATIONS:
            loc_pat = re.compile(fr'\b{location}\b', re.IGNORECASE)
            if key and loc_pat.search(key):
                f.locations.append(location)
            elif not key and loc_pat.search(value):
                logging.warning(f'Possible unrecognized finding separator in "{s}"')
                f.locations.append(location)
        if prev_locations and not f.locations:
            f.locations = prev_locations
        else:
            f.locations = StandardTerminology.standardize_locations(f.locations)
        # there should only be one
        f.count = max(NumberConvert.contains(patterns.SIZE_PATTERN.sub(' ', value), ['polyp'], 2,
                                             split_on_non_word=True) + [1])
        f.removal = 'remove' in value or 'retriev' in value
        # size
        for m in patterns.SIZE_PATTERN.finditer(
                patterns.AT_DEPTH_PATTERN.sub(' ', value)
        ):
            num = m.group(1)
            if num[0] == '<':
                size = float(num[1:]) - 0.1
            else:
                size = float(num)
            if m.group().strip()[-2] == 'c':  # mm
                size *= 10  # convert to mm
            if size > 100:
                continue
            if not f.size or size > f.size:  # get largest size only
                f.size = size
        return f


class CspyManager:
    _Wn = r'[^\w\n]'
    TITLE_PATTERN = re.compile(rf'([A-Z][a-z]+{_Wn}?(?:[A-Z][a-z]+{_Wn}?|and\s|of\s)*:|[A-Z]+:)')
    ENUMERATE_PATTERN = re.compile(r'\d[\)\.]')
    FINDINGS = 'FINDINGS'
    INDICATIONS = 'INDICATIONS'
    LABELS = {
        FINDINGS: ['Findings', 'Impression'],
        INDICATIONS: ['INDICATIONS'],
    }

    def __init__(self, text):
        self.text = text
        self.title = ''
        self.sections = {}
        self._get_sections()
        self._findings = self.get_findings()
        if self._findings:
            self.num_polyps = max(sum(f.count for f in self._findings[src]) for src in self._findings)
        else:
            self.num_polyps = 0
        self.indication = self.get_indication()
        self.prep = self.get_prep()
        self.extent = self.get_extent()

    def __bool__(self):
        return bool(self.text.strip())

    def _get_sections(self):
        """
        Separate using Header: value
        Except:
            * header begins with enumeration (-,*) suggesting it is sublist
        :return:
        """
        curr = None
        prev_line_item = None
        for el in self.TITLE_PATTERN.split(self.text):
            if not el.strip():  # skip empty lines
                continue
            elif el.endswith(':') and not prev_line_item:
                curr = el[:-1]
                self.sections[curr] = ''
            elif curr is None:
                if not self.title:
                    self.title = el.strip()
                continue
            elif self.sections[curr]:  # spacing should already be included...just in case
                self.sections[curr] += ' ' + el
            else:
                self.sections[curr] += el
            prev_line_item = (
                    el.strip()[-1] in ['·', '•', '-', '*']
                    or self.ENUMERATE_PATTERN.match(el.strip()[-2:])
            )

    def _get_section(self, category):
        for label in self.LABELS[category]:
            if label in self.sections:
                sect = self.sections[label]
                if sect:
                    yield sect

    def get_findings(self):
        findings = collections.defaultdict(list)
        for label in self.LABELS[self.FINDINGS]:
            if label in self.sections:
                sect = self.sections[label]
                if not sect:  # empty string
                    continue
                sects = self._deenumerate(sect)
                self._parse_sections(findings, label, sects)
        return findings

    def _parse_sections(self, findings, label, sects):
        prev_locations = None
        for s in sects:
            prev_locations = self._parse_section(findings, label, prev_locations, s)

    @staticmethod
    def _parse_section(findings, label, prev_locations, s):
        f = Finding.parse_finding(s, prev_locations=prev_locations, source=label)
        if findings[label] and f.is_compatible(findings[label][-1]):
            findings[label][-1].merge(f)
        else:
            findings[label].append(f)
        return f.locations

    def get_indication(self):
        for sect in self._get_section(self.INDICATIONS):
            if INDICATION_DIAGNOSTIC.matches(sect):
                return Indication.DIAGNOSTIC
            elif INDICATION_SURVEILLANCE.matches(sect):
                return Indication.SURVEILLANCE
            elif INDICATION_SCREENING.matches(sect):
                return Indication.SCREENING
        return Indication.UNKNOWN

    def get_extent(self):
        if PROCEDURE_EXTENT.matches(self.text):
            return Extent.COMPLETE
        return Extent.UNKNOWN

    def get_prep(self):
        m = COLON_PREP_PRE.matches(self.text) or COLON_PREP_POST.matches(self.text)
        if m:
            res = m.groupdict('prep').lower()
            return ColonPrep.VALUES[res]

    def _deenumerate(self, sect):
        # find first list marker
        sect = sect.strip()
        if not sect:  # empty string
            return []
        if sect[:2] == '--':
            return re.compile(r'\W' + sect[:2]).split(sect[2:])
        elif sect[0] in ['·', '•', '-', '*']:
            # split on list marker, skip first
            return re.compile(r'\W' + sect[0]).split(sect[1:])
            # return sect[1:].split(sect[0])
        elif sect[0] in ['1'] and sect[1] in ')-.':
            pat = r'\W\d' + re.escape(sect[1])
            return re.compile(pat).split(sect[2:])
        if len(sect) > 100:
            # look for sentence splitting
            if ':' in sect:
                s = sect.split(':')[-1]
                res = self._deenumerate(s)
                if res:
                    return res
            else:  # sentence split
                # determine method of splitting based on larger results
                period_split = patterns.SSPLIT.split(sect)
                newline_split = patterns.NO_PERIOD_SENT.split(sect)
                if len(period_split) > len(newline_split):
                    return period_split
                return newline_split
            logging.warning(f'Did not find list marker to separate: "{sect[:50]}..."')
            return []
        return [sect]

    def get_findings_of_size(self, min_size=10):
        """
        Get locations of removed polyps of a given size or larger
        :param min_size: minimum size to return
        :return: location, size
        """
        res = []
        for f in self._findings:
            if f.size and f.size >= min_size:
                res.append(f)
        return res
