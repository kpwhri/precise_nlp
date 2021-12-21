import collections
import enum
from loguru import logger
import re
from typing import Iterable

from precise_nlp.const import patterns
from precise_nlp.const.patterns import INDICATION_DIAGNOSTIC, INDICATION_SURVEILLANCE, INDICATION_SCREENING, \
    PROCEDURE_EXTENT_COMPLETE, COLON_PREP_PRE, COLON_PREP_POST, PROCEDURE_EXTENT_INCOMPLETE, COLON_PREPARATION, \
    REMOVE_SCREENING, PROCEDURE_EXTENT_INCOMPLETE_PRE, PROCEDURE_EXTENT_ALL
from precise_nlp.extract.cspy.finding_builder import FindingBuilder, Finding
from precise_nlp.extract.cspy.finding_patterns import apply_finding_patterns_to_location, apply_finding_patterns, \
    remove_finding_patterns
from precise_nlp.extract.cspy.naive_finding import NaiveFinding
from precise_nlp.extract.utils import Indication, Extent, \
    ColonPrep, Prep, IndicationPriority, StandardTerminology


class FindingVersion(enum.Enum):
    BROAD = 1  # original version, summary-level
    PRECISE = 2  # precise focus


class CspyManager:
    _Wn = r'[^\w\n]'
    TITLE_PATTERN = re.compile(
        rf'('
        rf'EGD Indications'
        rf'|[A-Z][a-z]+{_Wn}?(?:[A-Z][a-z]+{_Wn}?|and\s|of\s)*:'
        rf'|[A-Z]+:'
        rf'|(?:Patient\W*)?(?:Active\W*)?\W*Problem List'
        rf')')
    ENUMERATE_PATTERN = re.compile(r'\d[).]')
    NOT_FINDING_PATTERN = re.compile(r'\b(exam|lesion)', re.I)
    FINDINGS = 'FINDINGS'
    INDICATIONS = 'INDICATIONS'
    LOCATION_SPECIFIED = 'LOCATION_SPECIFIED'
    LABELS = {
        FINDINGS: ['Findings', 'Impression', 'Impressions', LOCATION_SPECIFIED],
        INDICATIONS: ['INDICATIONS', 'Indications', 'Surveillance',
                      'Colonoscopy Indications',
                      ],
    }

    def __init__(self, text, *, version=FindingVersion.PRECISE, cspy_extent_search_all=False, test_skip_parse=False):
        """

        :param text:
        :param version:
        :param cspy_extent_search_all:
        :param test_skip_parse: for testing: don't run all the algorithms (expected that one would be run manually)
        """
        self.text = text
        self.title = ''
        self.sections = {}
        self._get_sections()
        self._findings = None
        self.num_polyps = None
        self._indication = None
        self._prep = None
        self._extent = None
        if not test_skip_parse:
            self.parse_sections(version=version, cspy_extent_search_all=cspy_extent_search_all)

    def parse_sections(self, *, version=FindingVersion.PRECISE, cspy_extent_search_all=False):
        self._findings = list(self._get_findings(version=version))
        if self._findings:
            self.num_polyps = sum(f.count for f in self._findings)
        else:
            self.num_polyps = 0
        self._indication = self.get_indication()
        self._prep = self.get_prep()
        self._extent = self.get_extent(cspy_extent_search_all=cspy_extent_search_all)

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
        # don't allow 'Polyp:' to create a new section
        text = re.sub(r'(polyps?)\W*?:', r'\1 ', self.text, flags=re.I)
        for el in self.TITLE_PATTERN.split(text):
            if not el.strip():  # skip empty lines
                continue
            elif (el.endswith(':') or 'Problem List' in el) and not prev_line_item:
                curr = el[:-1]
                if curr not in self.sections:
                    self.sections[curr] = []
            elif curr is None:
                if not self.title:
                    self.title = el.strip()
                continue
            else:
                if curr.lower() in StandardTerminology.LOCATIONS.values():
                    self.sections[self.LOCATION_SPECIFIED] = self.sections.get(self.LOCATION_SPECIFIED, list())
                    self.sections[self.LOCATION_SPECIFIED].append(f'{curr} - {el}')
                else:
                    self.sections[curr].append(el)
            # TODO: only allow certain sections to contain these lists??
            prev_line_item = (
                    (el.strip()[-1] in ['·', '•', '-', '*'] and '----' not in el)
                    or self.ENUMERATE_PATTERN.match(el.strip()[-2:])
            )

    def _get_section(self, category):
        for label in self.LABELS[category]:
            if label in self.sections:
                for sect in self.sections[label]:
                    if sect:
                        yield sect

    def _get_findings(self, version=FindingVersion.PRECISE):
        if version == FindingVersion.BROAD:
            return self._get_findings_broad()
        elif version == FindingVersion.PRECISE:
            return list(self.get_findings_precise())
        else:
            raise ValueError(f'Unrecognized Finding Version: {version}')

    def get_sections_by_label(self, *labels):
        """
        Semiheader portion handles multiple lines like:
        "* Cecum: \n0.5cm polyp" -- these are read as separate units
        :param labels:
        :return:
        """
        for label in labels:
            semiheader = None  # portion separated by colon, expected to be part of subsequent line
            for sect in self.sections.get(label, list()):
                if sect:
                    if not semiheader and sect.strip().endswith(':') and len(sect) < 20:
                        semiheader = sect.strip()
                    elif semiheader:
                        yield f'{semiheader} {sect}'
                        semiheader = None
                    else:
                        yield sect
            if semiheader:
                yield semiheader

    def get_findings_patterns(self, sect) -> tuple[str, list]:
        """

        :param sect: section as returned by `get_sections_by_label`
        :return: tuple with:
            1. text without the found terms for additional parsing
            2. list of current findings
        """
        locations = self.split_by_location(sect)
        findings = []
        if len(locations.keys()) > 4:
            for location, location_text in locations.items():
                for finding in apply_finding_patterns_to_location(location_text, location):
                    findings.append(finding)
            if len(findings) > 0:
                return '', findings
        findings = list(apply_finding_patterns(sect))
        if len(findings) > 0:
            sect = remove_finding_patterns(sect)
        return sect, findings

    def split_by_location(self, text):
        """
        Divide section by location; assumed to have delimiters of '-—:'
        :param text:
        :return:
        """
        pat = re.compile(
            rf'({StandardTerminology.LOCATION_PATTERN})\s*(colon|flexure)?\s*[-—:]',
            re.I
        )
        prev_location = None
        prev_end = None
        locations = {}
        for m in pat.finditer(text):
            location = tuple(StandardTerminology.convert_location(m.group(1)))
            if prev_location:
                locations[prev_location] = text[prev_end: m.start()].strip()
            prev_location = location
            prev_end = m.end()
        if prev_location and prev_end:
            locations[prev_location] = text[prev_end:].strip()
        return locations

    def get_findings_precise(self):
        findings_by_section = []
        for sect in self.get_sections_by_label(*self.LABELS[self.FINDINGS]):
            sect, findings = self.get_findings_patterns(sect)
            if sect:
                findings += [f for f in self.get_findings_precise_section(sect) if f]
            if findings:
                findings_by_section.append(findings)
        return self._merge_sections(sorted(findings_by_section, key=lambda x: -len(x)))

    def get_findings_precise_section(self, sect):
        fb = FindingBuilder()
        for segment in self._deenumerate(sect):
            fb.fsm(segment)
        yield from fb.split_findings2(*fb.get_merged_findings())

    def _merge_sections(self, findings_by_section):
        if not findings_by_section:
            return []
        if len(findings_by_section) == 1:
            return findings_by_section[0]
        result_findings = []
        # compare the first section against the other sections
        # sections are different groups of section headers
        # TODO: base section should be the most-documented (currently: first-appearing)
        for finding in findings_by_section[0]:
            for i, section in enumerate(findings_by_section[1:]):
                new_finding = None
                for j, curr_finding in enumerate(section):
                    if FindingBuilder.can_merge_findings(finding, curr_finding):
                        new_finding = FindingBuilder.merge_findings(finding, curr_finding)
                        break
                if new_finding:
                    section.pop(j)
                    finding = new_finding
            result_findings.append(finding)
        # TODO: handle remaining leftovers? or do comparison of total counts?
        return result_findings

    def _get_findings_broad(self):
        findings = collections.defaultdict(list)
        for label in self.LABELS[self.FINDINGS]:
            if label in self.sections:
                for sect in self.sections[label]:
                    if not sect:  # empty string
                        continue
                    sects = self._deenumerate(sect)
                    self._parse_sections(findings, label, sects)
        for section, values in findings.items():
            yield from values

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

    def _prioritize_indications(self, indications):
        if indications:
            for ind in IndicationPriority:
                if ind in indications:
                    return ind
        return None

    def _get_indications_from_indications_section(self):
        """
        2021-11-30: Adding keys as well
        :return:
        """
        return self._get_indications_from(self._get_section(self.INDICATIONS))

    def _get_indications(self, section):
        indications = []
        for sect in re.split(r'[.*:]\s+', section):  # sentence split for negation scope
            if m := REMOVE_SCREENING.matches(sect):
                logger.debug(f'INDICATIONS: Removing Screening {m.group()}.')
                # remove these terms from further consideration
                sect = REMOVE_SCREENING.sub('', sect)
                indications.append(Indication.SCREENING)
            if m := INDICATION_DIAGNOSTIC.matches(sect):
                logger.debug(f'INDICATIONS: Found Diagnostic {m.group()}.')
                indications.append(Indication.DIAGNOSTIC)
            elif m := INDICATION_SURVEILLANCE.matches(sect):
                logger.debug(f'INDICATIONS: Found Surveillance {m.group()}.')
                indications.append(Indication.SURVEILLANCE)
            elif m := INDICATION_SCREENING.matches(sect):
                logger.debug(f'INDICATIONS: Found Screening {m.group()}.')
                indications.append(Indication.SCREENING)
        return indications

    def _get_indications_from(self, iterator):
        indications = []
        for section in iterator:
            indications += self._get_indications(section)
        return self._prioritize_indications(indications)

    def get_indications_from_text_debug(self, text, ignore_negation=False):
        if m := INDICATION_DIAGNOSTIC.matches(text, ignore_negation=ignore_negation):
            return Indication.DIAGNOSTIC, m
        elif m := INDICATION_SURVEILLANCE.matches(text, ignore_negation=ignore_negation):
            return Indication.SURVEILLANCE, m
        elif m := INDICATION_SCREENING.matches(text, ignore_negation=ignore_negation):
            return Indication.SCREENING, m
        elif m := re.search(r'\bdiverti\w+', text, re.I):
            return Indication.UNKNOWN, m
        return Indication.UNKNOWN, None

    def _get_indications_from_keys(self):
        """
        Get indications from section keys. If key is positive, the value will
            be considered as well (but limit to 100 characters -- don't want full note).
        :return:
        """
        indications = []
        for key, value in self.sections.items():
            curr_indications = self._get_indications(key)
            if curr_indications:
                curr_indications += self._get_indications(' '.join(value)[:100])
            indications += curr_indications
        return self._prioritize_indications(indications)

    def _get_indications_from_header(self):
        """Look at entire header section for indication language"""
        m = re.compile(
            '(asa grade'  # in text of procedure (frequent)
            '|colonoscope'  # in text of procedure
            '|propofol'  # common medication, usually listed after indications
            '|ileum'  # text of procedure
            ')', re.I).search(self.text)
        if m:
            return self._get_indications_from([self.text[:m.start()]])

    def get_indication(self):
        """
        Find indications in 2 phases:
        1. Look in indications section + headers
            a. If header matches, look in associated value (section text) as well
        2. Look in entire header section for relevant values.
        :return:
        """
        indications = []
        if ind := self._get_indications_from_indications_section():
            indications.append(ind)
        if ind := self._get_indications_from_keys():
            indications.append(ind)
        if indications:
            return self._prioritize_indications(indications)
        if ind := self._get_indications_from_header():
            return ind
        return Indication.UNKNOWN

    def get_extent(self, *, cspy_extent_search_all=False):
        if PROCEDURE_EXTENT_INCOMPLETE_PRE.matches(self.text):
            return Extent.INCOMPLETE
        elif PROCEDURE_EXTENT_COMPLETE.matches(self.text):
            return Extent.COMPLETE
        elif PROCEDURE_EXTENT_INCOMPLETE.matches(self.text):
            return Extent.INCOMPLETE
        if PROCEDURE_EXTENT_ALL.matches(self.text):
            if cspy_extent_search_all:
                return Extent.COMPLETE
            return Extent.POSSIBLE_COMPLETE
        return Extent.UNKNOWN

    def get_prep(self):
        m = (COLON_PREP_PRE.matches(self.text)
             or COLON_PREP_POST.matches(self.text)
             or COLON_PREPARATION.matches(self.text)
             )
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
        elif '\n' in sect:
            return sect.split('\n')
        if len(sect) > 100:
            # look for sentence splitting
            if ':' in sect:
                header, *s = sect.split(':')
                s = ':'.join(s)  # HACK: capturing multiple colons; the other colons are likely other sections
                if header.lower() in StandardTerminology.LOCATIONS.values():
                    return [sect]
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
        for findings in self._findings:
            for f in findings:
                if f.size and f.size >= min_size:
                    res.append(f)
        return res

    def get_findings(self) -> Iterable[Finding]:
        for finding in self._findings:
            if finding.count > 0:
                yield finding
