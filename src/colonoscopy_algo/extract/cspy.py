import collections
import logging
import re

from colonoscopy_algo.const import patterns
from colonoscopy_algo.const.patterns import INDICATION_DIAGNOSTIC, INDICATION_SURVEILLANCE, INDICATION_SCREENING, \
    PROCEDURE_EXTENT_COMPLETE, COLON_PREP_PRE, COLON_PREP_POST, PROCEDURE_EXTENT_INCOMPLETE
from colonoscopy_algo.extract.utils import NumberConvert, depth_to_location, StandardTerminology, Indication, Extent, \
    ColonPrep, Prep, IndicationPriority


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
        self._count = count
        self.removal = removal
        self.size = size
        self.source = None

    def __repr__(self):
        return f'<{self.count}{{}}@{",".join(self.locations)}:{self.size}>'.format('removed' if self.removal else '')

    def __str__(self):
        return repr(self)

    @property
    def count(self):
        return self._count if self._count else 1

    def is_compatible(self, f):
        if not isinstance(f, Finding):
            raise ValueError('Can only compare findings')
        if self.source == f.source:
            if f.removal and not self.removal:  # removal is last item mentioned, usually
                return False
            elif self._count and f._count and self._count != f._count:  # counts must be the same
                return False
            elif set(self.locations) != set(f.locations):
                return False
            elif self.size and f.size:
                return False
        else:  # sources not equal
            if self._count and f._count and self._count != f._count:
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
        self._count = max(self._count, f._count)
        self.removal = self.removal or f.removal
        self.locations += f.locations
        if self.size and f.size:
            self.size = max(self.size, f.size)
        elif f.size:
            self.size = f.size

    def _locate_depth(self, pat, value):
        new_value = []
        end = 0
        for m in pat.finditer(value):
            if 'size' in value[m.end():m.end() + 15]:
                continue
            self.locations += depth_to_location(float(m.group(1)))
            new_value.append(value[end:m.start()])
            end = m.end()
        new_value.append(value[end:])
        return ' '.join(new_value)

    def _locate_size(self, pat, value):
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

    @staticmethod
    def parse_finding(s, prev_locations=None, source=None):
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
        f = Finding(source=source)
        # in size pattern
        value = f._locate_size(patterns.IN_SIZE_PATTERN, value)
        # look for location as an "at 10cm" expression
        value = f._locate_depth(patterns.AT_DEPTH_PATTERN, value)
        if not f.size:
            value = f._locate_size(patterns.SIZE_PATTERN, value)
        if not f.locations:
            # without at, require 2 digits and "CM"
            value = f._locate_depth(patterns.CM_DEPTH_PATTERN, value)
        # spelled-out locations
        for location in StandardTerminology.LOCATIONS:
            loc_pat = re.compile(fr'\b{location}\b', re.IGNORECASE)
            if key and loc_pat.search(key):
                f.locations.append(location)
            elif not key and loc_pat.search(value):
                logging.warning(f'Possible unrecognized finding separator in "{s}"')
                f.locations.append(location)
        # update locations if none found
        if prev_locations and not f.locations:
            f.locations = prev_locations
        else:
            f.locations = StandardTerminology.standardize_locations(f.locations)
        # there should only be one
        f._count = max(NumberConvert.contains(value, ['polyp', 'polyps'], 2,
                                              split_on_non_word=True) + [0])
        f.removal = 'remove' in value or 'retriev' in value
        return f

    def is_standalone(self, prev_locations):
        """Need more than just removal and prev_locations"""
        if self.locations != prev_locations:
            return True
        elif self.size:
            return True
        elif self._count:
            return True
        return False


class CspyManager:
    _Wn = r'[^\w\n]'
    TITLE_PATTERN = re.compile(
        rf'('
        rf'[A-Z][a-z]+{_Wn}?(?:[A-Z][a-z]+{_Wn}?|and\s|of\s)*:'
        rf'|[A-Z]+:'
        rf'|(?:Patient\W*)?(?:Active\W*)?\W*Problem List'
        rf')')
    ENUMERATE_PATTERN = re.compile(r'\d[\)\.]')
    NOT_FINDING_PATTERN = re.compile(r'\b(exam|lesion)', re.I)
    FINDINGS = 'FINDINGS'
    INDICATIONS = 'INDICATIONS'
    LABELS = {
        FINDINGS: ['Findings', 'Impression'],
        INDICATIONS: ['INDICATIONS', 'Indications'],
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
        self._indication = self.get_indication()
        self._prep = self.get_prep()
        self._extent = self.get_extent()

    @property
    def indication(self):
        return self._indication.name if self._indication else self._indication

    @property
    def prep(self):
        return self._prep.name if self._prep else self._prep

    @property
    def extent(self):
        return self._extent.name if self._extent else self._extent

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
            elif (el.endswith(':') or 'Problem List' in el) and not prev_line_item:
                curr = el[:-1]
                if curr not in self.sections:
                    self.sections[curr] = ''
            elif curr is None:
                if not self.title:
                    self.title = el.strip()
                continue
            elif self.sections[curr]:  # spacing should already be included...just in case
                self.sections[curr] += ' ' + el
            else:
                self.sections[curr] += el
            # TODO: only allow certain sections to contain these lists??
            prev_line_item = (
                (el.strip()[-1] in ['·', '•', '-', '*'] and not '----' in el)
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
            if self.NOT_FINDING_PATTERN.search(s):
                continue
            prev_locations = self._parse_section(findings, label, prev_locations, s)

    @staticmethod
    def _parse_section(findings, label, prev_locations, s):
        f = Finding.parse_finding(s, prev_locations=prev_locations, source=label)
        if findings[label] and f.is_compatible(findings[label][-1]):
            findings[label][-1].merge(f)
        elif f.is_standalone(prev_locations):
            findings[label].append(f)
        return list(set(f.locations))

    def get_indication(self):
        indications = []
        for sect in self._get_section(self.INDICATIONS):
            if INDICATION_DIAGNOSTIC.matches(sect):
                indications.append(Indication.DIAGNOSTIC)
            elif INDICATION_SURVEILLANCE.matches(sect):
                indications.append(Indication.SURVEILLANCE)
            elif INDICATION_SCREENING.matches(sect):
                indications.append(Indication.SCREENING)
        if indications:
            for ind in IndicationPriority:
                if ind in indications:
                    return ind
        return Indication.UNKNOWN

    def get_extent(self):
        if PROCEDURE_EXTENT_COMPLETE.matches(self.text):
            return Extent.COMPLETE
        elif PROCEDURE_EXTENT_INCOMPLETE.matches(self.text):
            return Extent.INCOMPLETE
        return Extent.UNKNOWN

    def get_prep(self):
        m = COLON_PREP_PRE.matches(self.text) or COLON_PREP_POST.matches(self.text)
        if m:
            res = m.groupdict('prep').lower()
            return ColonPrep.VALUES[res]
        return Prep.UNKNOWN

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
        for section, findings in self._findings.items():
            for f in findings:
                if f.size and f.size >= min_size:
                    res.append(f)
        return res
