import logging
import re

from colonoscopy_algo.extract import patterns
from colonoscopy_algo.extract.parser import NumberConvert, depth_to_location, standardize_locations


class Finding:
    LOCATIONS = [
        'ileum', 'cecum', 'ascending', 'transverse',
        'descending', 'sigmoid', 'rectum', 'anorectum'
    ]

    def __init__(self, location=None, count=0, removal=None, size=None):
        """

        :param location:
        :param count:
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

    @staticmethod
    def parse_finding(s):
        if '-' in s:
            key, value = s.lower().split('-', maxsplit=1)
        elif ':' in s:
            key, value = s.lower().split(':', maxsplit=1)
        else:
            key = None
            value = s.lower()
        f = Finding()
        for location in Finding.LOCATIONS:
            if key and location in key:
                f.locations.append(location)
            elif not key and location in value:
                logging.warning(f'Possible unrecognized finding separator in "{s}"')
                f.locations.append(location)
        # look for location as an "at 10cm" expression
        for m in patterns.AT_DEPTH_PATTERN.finditer(value):
            f.locations += depth_to_location(float(m.group(1)))
        # without at, require 2 digits and "CM"
        for m in patterns.CM_DEPTH_PATTERN.finditer(value):
            f.locations += depth_to_location(float(m.group(1)))
        f.locations = standardize_locations(f.locations)
        # there should only be one
        f.count = max(NumberConvert.contains(value, ['polyp'], 2, split_on_non_word=True) + [0])
        f.removal = 'remove' in value
        # size
        m = patterns.SIZE_PATTERN.search(
            patterns.AT_DEPTH_PATTERN.sub(' ', value)
        )
        if m:
            f.size = float(m.group(1))
            if m.group().strip()[-2] == 'm':  # mm
                f.size *= 10
            if f.size > 10:
                f.size = None
        return f


class CspyManager:
    TITLE_PATTERN = re.compile(r'([A-Z][a-z]+\W?(?:[A-Z][a-z]+\W?|and\s|of\s)*:)')
    ENUMERATE_PATTERN = re.compile(r'\d[\)\.]')
    FINDINGS = 'FINDINGS'
    LABELS = {
        FINDINGS: ['Findings', 'Impression']
    }

    def __init__(self, text):
        self.text = text
        self.title = ''
        self.sections = {}
        self._get_sections()
        self.findings = self.get_findings()

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

    def get_findings(self):
        findings = []
        for label in self.LABELS[self.FINDINGS]:
            if label in self.sections:
                sect = self.sections[label]
                if not sect:  # empty string
                    continue
                sects = self._deenumerate(sect)
                for s in sects:
                    findings.append(Finding.parse_finding(s))
        return findings

    def _deenumerate(self, sect):
        # find first list marker
        sect = sect.strip()
        if sect[0] in ['·', '•', '-', '*']:
            # split on list marker, skip first
            return re.compile(r'\W' + sect[0]).split(sect[1:])
            # return sect[1:].split(sect[0])
        elif sect[0] in ['1'] and sect[1] in ')-.':
            pat = r'\W\d' + re.escape(sect[1])
            return re.compile(pat).split(sect[2:])
        if len(sect) > 100:
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
        for f in self.findings:
            if f.size and f.size >= min_size:
                res.append(f)
        return res
