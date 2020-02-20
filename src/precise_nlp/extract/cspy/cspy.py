import collections
import enum
from loguru import logger
import re

from precise_nlp.const import patterns
from precise_nlp.const.patterns import INDICATION_DIAGNOSTIC, INDICATION_SURVEILLANCE, INDICATION_SCREENING, \
    PROCEDURE_EXTENT_COMPLETE, COLON_PREP_PRE, COLON_PREP_POST, PROCEDURE_EXTENT_INCOMPLETE
from precise_nlp.extract.cspy.finding_builder import FindingBuilder
from precise_nlp.extract.cspy.naive_finding import NaiveFinding
from precise_nlp.extract.utils import Indication, Extent, \
    ColonPrep, Prep, IndicationPriority


class FindingVersion(enum.Enum):
    BROAD = 1  # original version, summary-level
    PRECISE = 2  # precise focus


class CspyManager:
    _Wn = r'[^\w\n]'
    TITLE_PATTERN = re.compile(
        rf'('
        rf'[A-Z][a-z]+{_Wn}?(?:[A-Z][a-z]+{_Wn}?|and\s|of\s)*:'
        rf'|[A-Z]+:'
        rf'|(?:Patient\W*)?(?:Active\W*)?\W*Problem List'
        rf')')
    ENUMERATE_PATTERN = re.compile(r'\d[).]')
    NOT_FINDING_PATTERN = re.compile(r'\b(exam|lesion)', re.I)
    FINDINGS = 'FINDINGS'
    INDICATIONS = 'INDICATIONS'
    LABELS = {
        FINDINGS: ['Findings', 'Impression'],
        INDICATIONS: ['INDICATIONS', 'Indications'],
    }

    def __init__(self, text, version=FindingVersion.BROAD):
        self.text = text
        self.title = ''
        self.sections = {}
        self._get_sections()
        self._findings = self.get_findings(version=version)
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
                    (el.strip()[-1] in ['·', '•', '-', '*'] and '----' not in el)
                    or self.ENUMERATE_PATTERN.match(el.strip()[-2:])
            )

    def _get_section(self, category):
        for label in self.LABELS[category]:
            if label in self.sections:
                sect = self.sections[label]
                if sect:
                    yield sect

    def get_findings(self, version=FindingVersion.BROAD):
        if version == FindingVersion.BROAD:
            return self.get_findings_broad()
        elif version == FindingVersion.PRECISE:
            return self.get_findings_precise()
        else:
            raise ValueError(f'Unrecognized Finding Version: {version}')

    def get_sections_by_label(self, *labels):
        for label in labels:
            sect = self.sections.get(label, None)
            if sect:
                yield sect

    def get_findings_precise(self):
        for sect in self.get_sections_by_label(*self.LABELS[self.FINDINGS]):
            fb = FindingBuilder()
            for segment in self._deenumerate(sect):
                fb.fsm(segment)
            findings = fb.get_merged_findings()

    def get_findings_broad(self):
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
        f = NaiveFinding.parse_finding(s, prev_locations=prev_locations, source=label)
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
            logger.warning(f'Did not find list marker to separate: "{sect[:50]}..."')
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