import logging
import re

from collections import defaultdict
from enum import Enum

from colonoscopy_algo.const import patterns
from colonoscopy_algo.extract.utils import depth_to_location, Location


class AdenomaCountMethod(Enum):
    COUNT_IN_JAR = 1
    ONE_PER_JAR = 2


def jarreader(f):
    def wrapper(self, *args, **kwargs):
        if not self._jars_read:
            self._read_jars(**kwargs)
        return f(self, *args, **kwargs)

    return wrapper


class PathManager:

    def __init__(self, text):
        self.text = text
        self.specs, self.specs_combined, self.specs_dict = PathManager.parse_jars(text)
        self.manager = JarManager()
        self._jars_read = False

    def _read_jars(self, **kwargs):
        for i, (name, sections) in enumerate(self.specs_dict.items()):
            # first section is diagnosis
            self.manager.cursory_diagnosis_examination(sections[0])
            # remaining sections are treated as a unit
            others = sections[1:]
            # sometimes locations appear in immediately subsequent section after dx
            if others:
                self.manager.find_locations(sections[1])
            # extract polyp sizes
            self.manager.extract_sizes(sections, i)
        # postprocessing all jars
        self._read_jars_postprocess()
        self._jars_read = True

    def _read_jars_postprocess(self):
        """
        Do cleanup logic to populate locations, etc.
        :return:
        """
        self.manager.postprocess()

    @jarreader
    def get_adenoma_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        return self.manager.get_adenoma_count(method)

    @jarreader
    def get_adenoma_distal_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        return self.manager.get_adenoma_distal_count(method)

    @jarreader
    def get_adenoma_proximal_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        return self.manager.get_adenoma_proximal_count(method)

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
            if not text.strip():  # first round 'A' might include empty string
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
        # special cases
        if 'b' in specimens_dict \
                and len(specimens_dict['a']) > len(specimens_dict['b']) \
                and len(specimens_dict['a'][0]) > 100:
            # contains intro text: don't recall example, but assuming it's long
            specimens_dict['a'] = specimens_dict['a'][1:]
        # accounts for preview text, like 'DIAGNOSIS: A) Colon...'
        elif 'b' in specimens_dict \
                and len(specimens_dict['a']) == len(specimens_dict['b']) + 1 \
                and len(specimens_dict['a'][0]) < 30:
            if 'received' in specimens_dict['a'][0].lower() or 'diagnosis' in specimens_dict['a'][0].lower():
                # skip intro section
                specimens_dict['a'] = specimens_dict['a'][1:]
            else:
                # retain intro section
                specimens_dict['a'] = [' '.join(specimens_dict['a'][:2])] + specimens_dict['a'][2:]

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

    @jarreader
    def get_locations_with_adenoma(self):
        return self.manager.get_locations_with_adenoma()

    @jarreader
    def get_locations_with_size(self, min_size):
        return self.manager.get_locations_with_size(min_size)


class PolypSize:
    """
    Captures and parses the size

    Exposes a PATTERN that can be used to iterate through found items
    """

    _COUNT = r'a|an|one|two|three|four|five|six|seven|eight|nine|\d'
    _TYPE = r'(cm|mm)?'
    _MEASURE = r'\d{1,2}\.?\d{,2}'
    PATTERN = re.compile(f'(?P<count>{_COUNT})?\W*'  # number
                         f'(?:(?P<min1>{_MEASURE})\W*{_TYPE}'  # min size (or only size)
                         f'(?:\W*x\W*(?P<min2>{_MEASURE})\W*{_TYPE}'
                         f'(?:\W*x\W*(?P<min3>{_MEASURE})\W*{_TYPE})?)?)'
                         f'(?:(?:up\W*to|to|-|and)\W*'
                         f'(?P<max1>{_MEASURE})\W*{_TYPE}'  # max size if exists
                         f'(?:\W*x\W*(?P<max2>{_MEASURE})\W*{_TYPE}'
                         f'(?:\W*x\W*(?P<max3>{_MEASURE})\W*{_TYPE})?)?)?')

    def __init__(self, text=''):
        self.count = 1
        self.min_size = None
        self.max_size = None
        self.max_dim = None
        if text:
            self._parse_text(text)

    def _parse_text(self, text):
        m = self.PATTERN.match(text)
        if not m:
            raise ValueError('Text does not match pattern!')
        if 'x' not in m.group() and '-' not in m.group() \
                and 'to' not in m.group() and 'and' not in m.group():
            raise ValueError('Only one-dimensional value: {}'.format(m.group()))
        cm = False
        if 'cm' in m.groups():
            cm = True
        self.min_size = self._parse_groups(m, cm=cm)
        mx = self._parse_groups(m, gname='max', cm=cm)
        self.max_size = mx if mx else self.min_size
        if self.min_size[0] >= 100.0:
            raise ValueError('Too big!')
        if self.max_size[0] >= 100.0:
            raise ValueError('Too big!')
        if len(self.min_size) + len(mx) <= 1:
            raise ValueError('Only one-dimensional value: {}'.format(m.group()))

    def _parse_groups(self, m, cm=False, gname='min'):
        lst = filter(None, [
            m.group(f'{gname}1'),
            m.group(f'{gname}2'),
            m.group(f'{gname}3')
        ])
        return sorted([float(m) * 10 if cm else float(m) for m in lst], reverse=True)

    def get_max_dim(self):
        return self.max_size[0]

    def __lt__(self, other):
        if not isinstance(other, PolypSize):
            raise ValueError('PolypSize object not sortable with {}'.format(type(other)))
        return self.get_max_dim() < other.get_max_dim()

    @classmethod
    def set(cls, *args):
        """Set size in millimeters"""
        c = cls()
        args = sorted(args)
        if len(args) > 3:
            c.max_size = tuple(args[:3])
            c.min_size = tuple(args[3:6])
        else:
            c.max_size = c.min_size = tuple(args)
        return c


class Jar:

    def __init__(self):
        self.kinds = []
        self.polyps = []
        self.polyp_count = MaybeCounter(1)
        self.adenoma_count = MaybeCounter(0)
        self.adenoma_distal_count = MaybeCounter(0)
        self.adenoma_proximal_count = MaybeCounter(0)
        self.locations = []
        self.histology = []
        self.polyp_size = []
        self.dysplasia = False
        self.depth = None

    def pprint(self):
        return '''Kinds: {}
        Polyp (Adenoma): {} {}
        '''.format(
            ','.join(self.kinds),
            self.polyp_count, self.adenoma_count
        )

    def set_depth(self, depth: float):
        """
        Based off: https://training.seer.cancer.gov/colorectal/anatomy/figure/figure1.html
        :param depth:
        :return:
        """
        self.add_locations(depth_to_location(depth))

    def set_polyp_size(self, size: float, cm=False):
        """

        :param size:
        :param cm: if size in centimeters (default: millimeters)
        :return:
        """
        if cm:
            size *= 10
        self.polyp_size.append(PolypSize.set(size))

    def add_locations(self, locations):
        self.locations += Location.standardize_locations(locations)

    def add_location(self, location):
        self.add_locations([location])


class JarManager:
    # https://www.cancer.gov/publications/dictionaries/cancer-terms/def/distal-colon
    # technically, does not include rectum, though I've included it
    DISTAL_LOCATIONS = ['descending', 'sigmoid', 'distal', 'rectum', 'splenic', 'left']
    # https://www.ncbi.nlm.nih.gov/pubmedhealth/PMHT0022241/
    PROXIMAL_LOCATIONS = ['proximal', 'ascending', 'transverse', 'cecum', 'hepatic', 'right']
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
        self.curr_jar = None

    def _adenoma_negated(self, section):
        if section.has_before(self.ADENOMA_NEGATION) and not section.has_before(self.HISTOLOGY, window=4):
            return True
        elif section.has_before('or', window=3) and section.has_before(self.ADENOMA_NEGATION, window=7):
            return True
        return False

    def is_distal(self, jar):
        """
        Distal if location includes a distal_location keyword
        Cite for locations:
            - https://www.cancer.gov/publications/dictionaries/cancer-terms/def/distal-colon
            - http://cebp.aacrjournals.org/content/17/5/1144
        Cite for distance: https://training.seer.cancer.gov/colorectal/anatomy/figure/figure1.html
        :param jar:
        :return:
        """
        return bool(set(jar.locations) & set(self.DISTAL_LOCATIONS) and
                    not set(jar.locations) | set(self.DISTAL_LOCATIONS)) or bool(jar.depth and jar.depth < 82)

    def maybe_distal(self, jar):
        return bool(set(jar.locations) & set(self.DISTAL_LOCATIONS))

    def is_proximal(self, jar):
        """
        Proximal if location includes a proximal_location keyword
        Cite for locations:
            - https://www.cancer.gov/publications/dictionaries/cancer-terms/def/distal-colon
            - http://cebp.aacrjournals.org/content/17/5/1144
        Cite for distance: https://training.seer.cancer.gov/colorectal/anatomy/figure/figure1.html
        Proximal defn: https://www.ncbi.nlm.nih.gov/pubmedhealth/PMHT0022241/
        :param jar:
        :return:
        """
        return bool(set(jar.locations) & set(self.PROXIMAL_LOCATIONS) and
                    not set(jar.locations) | set(self.PROXIMAL_LOCATIONS)) or bool(jar.depth and jar.depth >= 82)

    def maybe_proximal(self, jar):
        return bool(set(jar.locations) & set(self.PROXIMAL_LOCATIONS))

    def add_count_to_jar(self, jar, count=1, greater_than=False, at_least=False):
        jar.adenoma_count.add(count, greater_than, at_least)

    def cursory_diagnosis_examination(self, section):
        jar = Jar()
        section = PathSection(section)
        found_polyp = False
        for word in section:
            if word.isin(Location.LOCATIONS):
                if word.isin(['distal', 'proximal']) and section.has_after(Location.LOCATIONS, window=3):
                    continue  # distal is descriptive of another location (e.g., distal transverse)
                jar.add_location(word)
            elif word.matches(patterns.DEPTH_PATTERN) and 'cm' in word.word \
                    or word.matches(patterns.NUMBER_PATTERN) \
                    and section.has_after(['cm'], window=1):
                # 15 cm, etc.
                num = float(word.match(patterns.NUMBER_PATTERN))
                if num < 10:
                    if section.has_after(['dimension', 'maximal', 'maximum'], window=4):
                        # might be polyp dimensions
                        jar.set_polyp_size(num, cm=True)
                else:  # must be >= 10cm
                    jar.set_depth(num)
            elif word.matches(patterns.DEPTH_PATTERN) and 'mm' in word.word \
                    or word.matches(patterns.NUMBER_PATTERN) \
                    and section.has_after(['mm'], window=1):
                # 15 cm, etc.
                jar.set_depth(float(word.match(patterns.NUMBER_PATTERN)) / 10)
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
                    self.add_count_to_jar(jar, 1)
                if num and has_frags:
                    self.add_count_to_jar(jar, 1, at_least=True)
                elif num:  # identified number
                    self.add_count_to_jar(jar, self.NUMBER_CONVERT[str(num)])
                else:  # default case
                    self.add_count_to_jar(jar, 1, greater_than=True)

            elif word.isin(self.ADENOMA):
                if not self._adenoma_negated(section):
                    if section.has_before(self.FRAGMENTS, window=4):
                        self.add_count_to_jar(jar, 1, at_least=True)
                    else:
                        self.add_count_to_jar(jar, 1)
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
        self.curr_jar = len(self.jars) - 1
        return self

    def get_current_jar(self):
        if self.curr_jar is not None:
            return self.jars[self.curr_jar]
        raise ValueError('No current jar')

    def postprocess(self):
        """
        Post-processing steps to assign locations to various components, etc.
        :return:
        """
        for jar in self.jars:
            if self.is_distal(jar):
                jar.adenoma_distal_count = jar.adenoma_count
            elif self.maybe_distal(jar):  # be conservative
                if jar.adenoma_count:
                    jar.adenoma_distal_count.add(0, greater_than=True)
            if self.is_proximal(jar):
                jar.adenoma_proximal_count = jar.adenoma_count
            elif self.maybe_proximal(jar):  # be conservative
                if jar.adenoma_count:
                    jar.adenoma_proximal_count.add(0, greater_than=True)

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

    def get_adenoma_proximal_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        """

        :param method: AdenomaCountMethod - per jar or total number
        :return:
        """
        count = MaybeCounter(0)
        for jar in self.jars:
            if method == AdenomaCountMethod.COUNT_IN_JAR:
                count += jar.adenoma_proximal_count
            elif method == AdenomaCountMethod.ONE_PER_JAR:
                count += 1 if jar.adenoma_proximal_count else 0
        return count

    def get_locations_with_adenoma(self):
        locations = []
        for jar in self.jars:
            if jar.adenoma_count.gt(0) == 1:
                if len(jar.locations) > 0:
                    locations += Location.filter_colon(jar.locations)
                else:
                    locations.append(None)
        return locations

    def get_locations_with_size(self, min_size):
        locations = []
        for jar in self.jars:
            if jar.polyp_size and sorted(jar.polyp_size, reverse=True)[0].get_max_dim() >= min_size:
                if len(jar.locations) > 0:
                    locations += Location.filter_colon(jar.locations)
                else:
                    locations.append(None)
        return locations

    def extract_sizes(self, sections, jar_index):
        for section in sections:
            if len(self.jars) <= jar_index:
                jar = Jar()
                self.jars.append(jar)
            else:  # jar already parsed
                jar = self.jars[jar_index]
            for m in PolypSize.PATTERN.finditer(section):
                try:
                    jar.polyp_size.append(PolypSize(m.group()))
                except ValueError as e:
                    if 'big' not in str(e) and 'one' not in str(e):
                        raise e

    def find_locations(self, section):
        jar = self.get_current_jar()
        section = PathSection(section)
        for word in section:
            if word.isin(Location.LOCATIONS):
                if word.isin(['distal', 'proximal']) and section.has_after(Location.LOCATIONS, window=3):
                    continue  # distal is descriptive of another location (e.g., distal transverse)
                jar.add_location(word)


class PathSection:
    WORD_SPLIT_PATTERN = re.compile(r'([a-z]+|[0-9]+(?:\.[0-9]+)?)')
    STOP = re.compile('.*(:|\.).*')
    PREPROCESS = {re.escape(k): v for k, v in {
        'tubularadenoma': 'tubular adenoma',
        'tubularadenomas': 'tubular adenomas',
        'multipletubular': 'multiple tubular',
        'noevidence': 'no evidence',
    }.items()}
    PREPROCESS_RX = re.compile("|".join(PREPROCESS.keys()))

    def __init__(self, section):
        pword = None
        pindex = 0
        section = self._preprocess(section)
        self.section = []
        for m in self.WORD_SPLIT_PATTERN.finditer(self._preprocess(section)):
            if pword:  # get intervening punctuation
                self.section.append(PathWord(pword, section[pindex:m.start()]))
            pword = section[m.start(): m.end()]
            pindex = m.end()
        if pword:
            self.section.append(PathWord(pword, section[pindex:]))
        self.curr = None

    def _preprocess(self, text):
        return self.PREPROCESS_RX.sub(lambda m: self.PREPROCESS[re.escape(m.group(0))], text, re.IGNORECASE)

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
        self.spl = spl  # not part of object itself

    def isin(self, lst):
        return self.word in lst

    def matches(self, pattern):
        return pattern.match(self.word)

    def match(self, pattern):
        return pattern.match(self.word).group(1)

    def stop(self):
        return PathSection.STOP.match(self.spl)

    def __eq__(self, other):
        """Does not rely on punctuation"""
        if isinstance(other, PathWord):
            return self.word == other.word
        return self.word == other

    def __contains__(self, other):
        return other in self.word

    def __str__(self):
        return self.word

    def __bool__(self):
        return True

    def __hash__(self):
        """Does not rely on punctuation"""
        return hash(self.word)


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

    def __bool__(self):
        return self.count > 0 or self.greater_than

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
