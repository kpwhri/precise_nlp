import logging
import re

from collections import defaultdict
from enum import Enum


class AdenomaCountMethod(Enum):
    COUNT_IN_JAR = 1
    ONE_PER_JAR = 2

class PathManager:

    def __init__(self, text):
        self.text = text
        self.specs, self.specs_combined, self.specs_dict = PathManager.parse_jars(text)
        self.manager = JarManager()
        self._jars_read = False

    def _read_jars(self):
        for name, sections in self.specs_dict.items():
            # first section is diagnosis
            self.manager.cursory_diagnosis_examination(sections[0])
            # remaining sections are treated as a unit
            others = sections[1:]
        self._jars_read = True

    def get_adenoma_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        if not self._jars_read:
            self._read_jars()
        return self.manager.get_adenoma_count(method)

    def get_adenoma_distal_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        if not self._jars_read:
            self._read_jars()
        return self.manager.get_adenoma_distal_count(method)

    @staticmethod
    def parse_jars(text):
        specimens = [x.lower() for x in re.split(r'(?<!\()\W[A-Z]\)', text)]
        specimens_dict = defaultdict(list)
        it = iter(['A'] + re.split(
            r'(?:^|[^a-zA-Z0-9_\(])'
            r'([A-Z](?:\D?(?:and|-|,|&)\D?[A-Z])*)(?:\d(?:-\d)?)?\)',
            text
        ))
        for x in it:
            comment = None
            x = x.lower()
            text = next(it).lower()
            if not text:  # first round 'A' might include empty string
                continue
            if 'comment:' in text:
                idx = text.index('comment:')
                text = text[:idx]
                comment = text[idx:]
            if '-' in x or ',' in x or 'and' in x or '&' in x:
                for spec in PathManager.parse_specimen_range(x):
                    specimens_dict[spec].append(text)
                    if comment:
                        specimens_dict[spec].append(comment)
            else:
                specimens_dict[x].append(text)
                if comment:
                    specimens_dict[x].append(comment)
        specimens_combined = [' '.join(spec) for spec in specimens_dict.values()]
        return specimens, specimens_combined, specimens_dict

    @staticmethod
    def parse_specimen_range(s):
        chars = []
        pchar = None
        i = 0
        while i < len(s):
            char = s[i]
            if char in ['-', ',', '&']:
                pchar = char
            elif char == 'a' and i + 1 < len(s) and s[i + 1] == 'n' and s[i + 2] == 'd':
                pchar = ','
                i += 3
            elif char in range(0, 10):
                pass  # ignore numbers
            else:
                val = ord(char)
                if val in range(97, 123):
                    if pchar == '-':
                        chars += [chr(x) for x in range(ord(chars[-1]) + 1, val + 1)]
                    elif pchar == ',' or pchar == '&':
                        chars.append(char)
                    else:
                        chars.append(char)
                    pchar = char
            i += 1
        return chars


class Jar:

    def __init__(self):
        self.kinds = []
        self.polyps = []
        self.polyp_count = MaybeCounter(1)
        self.adenoma_count = MaybeCounter(0)
        self.adenoma_distal_count = MaybeCounter(0)
        self.locations = []
        self.histology = []
        self.dysplasia = False

    def pprint(self):
        return '''Kinds: {}
        Polyp (Adenoma): {} {}
        '''.format(
            ','.join(self.kinds),
            self.polyp_count, self.adenoma_count
        )


class JarManager:

    LOCATIONS = ['ascending', 'descending',
                 'transverse', 'sigmoid',
                 'hepatic', 'splenic',
                 'duodenum'
                 ]
    POLYPS = ['polyps', 'biopsies', 'polyp']
    POLYP = ['polyp']
    ADENOMAS = ['adenomas']
    ADENOMA = ['adenoma', 'adenomatoid', 'adenomatous',
               'adenomat',
               'adenom'  # abbreviation in early path reports
               ]
    COLON = ['colon', 'rectum', 'rectal', 'cecal',
             'cecum', 'colonic'
             ]
    FRAGMENTS = ['segments', 'fragments', 'pieces']
    FRAGMENT = ['segment', 'fragment', 'piece']
    ADENOMA_NEGATION = {'no', 'history', 'hx', 'sessile'}
    HISTOLOGY = ['tubulovillous', 'villous', 'tubular']
    NUMBER = {'one', 'two', 'three', 'four', 'five', 'six',
              'seven', 'eight', 'nine'} | {str(i) for i in range(10)}
    NUMBER_CONVERT = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    }
    NUMBER_CONVERT.update({str(i): i for i in range(10)})

    DYSPLASIA = {'dysplasia'}
    HIGHGRADE_DYS = {'highgrade', 'grade', 'severe'}

    def __init__(self):
        self.jars = []

    def _adenoma_negated(self, section):
        if section.has_before(self.ADENOMA_NEGATION) and not section.has_before(self.HISTOLOGY, window=4):
            return True
        elif section.has_before('or', window=3) and section.has_before(self.ADENOMA_NEGATION, window=7):
            return True
        return False

    def cursory_diagnosis_examination(self, section):
        jar = Jar()
        section = PathSection(section)
        found_polyp = False
        for word in section:
            if word.isin(self.LOCATIONS):
                jar.locations.append(word)
            elif not found_polyp and word.isin(self.POLYPS):  # polyps/biopsies
                if section.has_before(self.ADENOMA_NEGATION):
                    continue
                num = section.has_after(self.NUMBER, window=2)
                if not num or section.has_after(self.FRAGMENTS, window=4):
                    num = section.has_before(self.NUMBER, window=3)
                if num and not section.has_before(self.FRAGMENTS, window=2):
                    jar.polyp_count.set(self.NUMBER_CONVERT[str(num)])
                elif not word.isin(self.POLYP):
                    jar.polyp_count.greater_than = True
                found_polyp = True
            elif (
                word.isin(self.ADENOMAS) or
                (word.isin(self.ADENOMA) and section.has_after(self.POLYPS, window=1))
            ):
                if self._adenoma_negated(section):
                    continue
                num = section.has_after(self.NUMBER, window=2)
                has_frags = section.has_before(self.FRAGMENTS, window=4)
                if num and not num.spl.startswith(')'):
                    if section.has_after(self.FRAGMENTS, window=4):
                        num = False
                if not num:
                    num = section.has_before(self.NUMBER, window=5)
                if section.has_before(self.FRAGMENT, window=4):
                    jar.adenoma_count.add(1)
                if num and has_frags:
                    jar.adenoma_count.add(1, at_least=True)
                elif num:  # identified number
                    jar.adenoma_count.add(self.NUMBER_CONVERT[str(num)])
                else:  # default case
                    jar.adenoma_count.add(1, greater_than=True)

            elif word.isin(self.ADENOMA):
                if not self._adenoma_negated(section):
                    if section.has_before(self.FRAGMENTS, window=4):
                        jar.adenoma_count.add(1, at_least=True)
                    else:
                        jar.adenoma_count.add(1)
                else:
                    logging.debug('NEGATED!')
            elif word.isin(self.COLON):
                jar.kinds.append('colon')
            elif word.isin(self.HISTOLOGY):
                jar.histology.append(word)
            elif word.isin(self.DYSPLASIA):
                if section.has_before(self.HIGHGRADE_DYS, 1):
                    jar.dysplasia = True
        logging.info('Adenoma Count for Jar: {}'.format(jar.adenoma_count))
        self.jars.append(jar)
        return self

    def get_adenoma_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        """

        :param method: AdenomaCountMethod - per jar or total number
        :return: MaybeCounter
        """
        count = MaybeCounter(0)
        for jar in self.jars:
            if method == AdenomaCountMethod.COUNT_IN_JAR:
                count += jar.adenoma_count
            elif method == AdenomaCountMethod.ONE_PER_JAR:
                count += 1 if jar.adenoma_count else 0
        return count

    def get_adenoma_distal_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        """

        :param method: AdenomaCountMethod - per jar or total number
        :return:
        """
        count = MaybeCounter(0)
        for jar in self.jars:
            if method == AdenomaCountMethod.COUNT_IN_JAR:
                count += jar.adenoma_distal_count
            elif method == AdenomaCountMethod.ONE_PER_JAR:
                count += 1 if jar.adenoma_distal_count else 0
        return count


class PathSection:

    WORD_SPLIT_PATTERN = re.compile(r'([a-z]+|[0-9]+(?:\.[0-9]+)?)')
    STOP = re.compile('.*(:|\.).*')
    
    def __init__(self, section):
        pword = None
        pindex = 0
        self.section = []
        for m in self.WORD_SPLIT_PATTERN.finditer(section):
            if pword:  # get intervening punctuation
                self.section.append(PathWord(pword, section[pindex:m.start()]))
            pword = section[m.start(): m.end()]
            pindex = m.end()
        if pword:
            self.section.append(PathWord(pword, section[pindex:]))
        self.curr = None
        
    def __iter__(self):
        for i, section in enumerate(self.section):
            self.curr = i
            yield section

    def has_before(self, terms, window=5, allow_stop=True):
        for word in reversed(self.section[max(self.curr - window, 0): self.curr]):
            if allow_stop and word.stop():
                return False
            if word.isin(terms):
                return word
        return False

    def has_after(self, terms, window=5, allow_stop=True):
        for word in self.section[self.curr + 1:min(self.curr + window + 1, len(self.section))]:
            if word.isin(terms):
                return word
            if allow_stop and word.stop():  # punctuation after word
                return False
        return False
        
    
class PathWord:
    
    def __init__(self, word, spl=''):
        self.word = word
        self.spl = spl
        
    def isin(self, lst):
        return self.word in lst

    def stop(self):
        return PathSection.STOP.match(self.spl)

    def __eq__(self, other):
        if isinstance(other, PathWord):
            return self.word == other.word
        return self.word == other

    def __contains__(self, other):
        return other in self.word

    def __str__(self):
        return self.word

    def __bool__(self):
        return True


class Polyp:

    def __init__(self):
        self.locations = []
        self.tubular = False
        self.villous = False


class MaybeCounter:
    """
    A counter to count with greater than or at least values
    """
    GREATER_THAN_LIMIT = 1

    def __init__(self, count=1, at_least=False, greater_than=False):
        if at_least and greater_than:
            raise ValueError('Value may only be "at_least" or "greater_than".')
        self.count = count
        self.at_least = at_least
        self.greater_than = greater_than

    def add(self, count=1, greater_than=False, at_least=False):
        if count >= 0:
            count = self.count + count
            gt = False
            al = self.at_least or self.greater_than or at_least or greater_than
            if self.greater_than and greater_than:
                count += 2
            elif self.greater_than or greater_than:
                count += 1
            self.greater_than = gt
            self.at_least = al
            self.count = count

    def set(self, count=0, greater_than=False, at_least=False):
        self.count = count
        self.greater_than = greater_than
        self.at_least = at_least

    def __add__(self, other):
        try:
            return MaybeCounter(self.count + int(other),
                                at_least=self.at_least,
                                greater_than=self.greater_than)
        except TypeError:
            pass
        count = self.count + other.count
        greater_than = False
        at_least = self.at_least or self.greater_than or other.at_least or other.greater_than
        if self.greater_than and other.greater_than:
            count += 2
        elif self.greater_than or other.greater_than:
            count += 1
        return MaybeCounter(count, at_least=at_least, greater_than=greater_than)

    def __sub__(self, other):
        try:
            return MaybeCounter(self.count - int(other),
                                at_least=self.at_least,
                                greater_than=self.greater_than)
        except TypeError:
            pass
        count = self.count - other.count
        greater_than = False
        at_least = self.at_least or self.greater_than or other.at_least or other.greater_than
        if self.greater_than and not other.greater_than:
            count += 1
            if other.at_least:
                at_least = False
        elif other.greater_than and not self.greater_than:
            count -= 1
            if self.at_least:
                at_least = False
        return MaybeCounter(count, at_least=at_least, greater_than=greater_than)

    def gt(self, other: int):
        if self.count > other:
            return 1
        elif self.count == other:
            if self.greater_than:
                return 1
            elif self.at_least:
                return 0
            else:
                return -1
        elif self.GREATER_THAN_LIMIT and self.greater_than and self.count + self.GREATER_THAN_LIMIT >= other:
                return 0
        elif self.GREATER_THAN_LIMIT and self.at_least and self.count + self.GREATER_THAN_LIMIT - 1 >= other:
                return 0
        return -1

    def eq(self, other: int):
        """

        :param other:
        :return: 1=exactly true; 0=maybe/possibly true
        """
        if self.count == other:
            if self.greater_than:
                return -1
            elif self.at_least:
                return 0
            else:
                return 1
        elif self.GREATER_THAN_LIMIT:
            if self.greater_than and self.count < other <= self.count + self.GREATER_THAN_LIMIT:
                return 0
            elif self.at_least and self.count - 1 < other <= self.count - 1 + self.GREATER_THAN_LIMIT:
                return 0
            else:
                return -1
        else:
            return -1

    def __str__(self):
        return '{}{}'.format(
            '>' if self.greater_than else '>=' if self.at_least else '',
            self.count
        )

    def __repr__(self):
        return '{}{}'.format(
            '>' if self.greater_than else '>=' if self.at_least else '',
            self.count
        )
