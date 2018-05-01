import re


class NumberConvert:
    VALUES = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    }
    VALUES.update({str(i): i for i in range(10)})

    @staticmethod
    def contains(text, followed_by=None, distance=0, split_on_non_word=False):
        results = []
        if split_on_non_word:
            text = re.split('\W+', text)
        else:
            text = text.split()
        dtext = {x: i for i, x in enumerate(text)}
        for val in set(dtext) & set(NumberConvert.VALUES):
            start = dtext[val] + 1
            if not followed_by or set(followed_by) & set(text[start:start + distance]):
                results.append(NumberConvert.VALUES[val])
        return results


class Finding:
    LOCATIONS = [
        'ileum', 'cecum', 'ascending', 'transverse',
        'descending', 'sigmoid', 'rectum', 'anorectum'
    ]
    DEPTH_PATTERN = re.compile(r'(\d{1,3})\W*[cm]m', re.IGNORECASE)

    def __init__(self, location=None, count=0, removal=None, size=None):
        """

        :param location:
        :param count:
        :param removal:
        :param size: in mm
        """
        self.location = location
        self.count = count
        self.removal = removal
        self.size = size

    @staticmethod
    def parse_finding(s):
        if '-' in s:
            key, value = s.lower().split('-')
        else:
            raise ValueError(f'Unrecognized finding separator in "{s}"')
        f = Finding()
        for location in Finding.LOCATIONS:
            if location in key:
                f.location = location
        # there should only be one
        f.count = max(NumberConvert.contains(key, ['polyp'], 2, split_on_non_word=True))
        f.removal = 'remove' in value
        # size
        m = Finding.DEPTH_PATTERN.search(value)
        if m:
            f.size = float(m.group(1))
            if m.group().strip()[-2] == 'c':
                f.size *= 10
        return f


class CspyManager:
    TITLE_PATTERN = re.compile(r'([A-Z][a-z]+\W?(?:[A-Z][a-z]+\W?|and\s)+:)')
    ENUMERATE_PATTERN = re.compile(r'\d[\)\.]')
    FINDINGS = 'FINDINGS'
    LABELS = {
        FINDINGS: ['Findings']
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
                sects = self._deenumerate(sect)
                for s in sects:
                    findings.append(Finding.parse_finding(s))
        return findings

    def _deenumerate(self, sect):
        # find first list marker
        sect = sect.strip()
        if sect[0] in ['·', '•', '-', '*']:
            # split on list marker, skip first
            return sect[1:].split(sect[0])
        raise ValueError(f'Did not find list marker to separate: "{sect[:50]}..."')

    def get_findings_of_size(self, min_size=10):
        """
        Get locations of removed polyps of a given size or larger
        :param min_size: minimum size to return
        :return: location, size
        """
        res = []
        for f in self.findings:
            if f.size >= min_size:
                res.append(f)
        return res
