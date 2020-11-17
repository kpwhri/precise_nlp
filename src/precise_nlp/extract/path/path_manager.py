import re

from collections import defaultdict

from precise_nlp.const.enums import AdenomaCountMethod
from precise_nlp.extract.path.jar_manager import JarManager


def jarreader(f):
    def wrapper(self, *args, **kwargs):
        if not self._jars_read:
            self._read_jars(**kwargs)
        return f(self, *args, **kwargs)

    return wrapper


class PathManager:

    def __init__(self, text):
        self.text = text
        if self.text:
            self.specs, self.specs_combined, self.specs_dict = PathManager.parse_jars(text)
        else:
            self.specs, self.specs_combined, self.specs_dict = None, None, None
        self.manager = JarManager()
        self._jars_read = False

    def __bool__(self):
        return bool(self.text.strip())

    def _read_jars(self, **kwargs):
        for i, (name, sections) in enumerate(self.specs_dict.items()):
            # first section is diagnosis
            self.manager.cursory_diagnosis_examination(sections[0])
            # remaining sections are treated as a unit
            others = sections[1:]
            # sometimes locations appear in immediately subsequent section after dx
            if others:
                self.manager.find_locations(sections[1])
                self.manager.check_dysplasia(sections[1])
            # extract polyp sizes
            self.manager.extract_sizes(sections[0], i)
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

    @jarreader
    def get_adenoma_rectal_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        return self.manager.get_adenoma_rectal_count(method)

    @jarreader
    def get_adenoma_unknown_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        return self.manager.get_adenoma_unknown_count(method)

    @jarreader
    def get_sessile_serrated_count(self, jar_count=True):
        return self.manager.get_sessile_serrated_count(jar_count=jar_count)

    @jarreader
    def get_carcinoma_count(self, jar_count=True):
        return self.manager.get_carcinoma_count(jar_count=jar_count)

    @jarreader
    def get_carcinoma_maybe_count(self, jar_count=True):
        return self.manager.get_carcinoma_maybe_count(jar_count=jar_count)

    @jarreader
    def get_carcinoma_in_situ_count(self, jar_count=True):
        return self.manager.get_carcinoma_in_situ_count(jar_count=jar_count)

    @jarreader
    def get_carcinoma_in_situ_maybe_count(self, jar_count=True):
        return self.manager.get_carcinoma_in_situ_maybe_count(jar_count=jar_count)

    @staticmethod
    def parse_jars(text):
        comment_pat = re.compile(r'comment(?:\W*\([A-Za-z]\))?:')
        specimens = [x.lower() for x in re.split(r'(?<!\()\W[A-Z]\)', text)]
        specimens_dict = defaultdict(list)
        it = iter(['A'] + re.split(
            r'(?:^|[^a-zA-Z0-9_(])'
            r'([A-Z](?:\D?(?:and|-|,|&)\D?[A-Z])*)(?:\d(?:-\d)?)?\)',
            text
        ))
        for x in it:
            comment = None
            x = x.lower()
            text = next(it).lower()
            if not text.strip():  # first round 'A' might include empty string
                continue
            m = comment_pat.search(text)
            if m:
                text = text[:m.start()]
                comment = text[m.end():]
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
        elif 'received' in specimens_dict['a'][0] and len(specimens_dict['a'][0]) < 30:
            specimens_dict['a'] = specimens_dict['a'][1:]
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
    def get_locations_with_large_adenoma(self):
        yield from self.manager.get_locations_with_large_adenoma()

    @jarreader
    def get_locations_with_unknown_adenoma_size(self):
        return self.manager.get_locations_with_unknown_adenoma_size()

    @jarreader
    def get_locations_with_adenoma_size(self, min_size=None, max_size=None):
        if min_size is not None:
            yield from self.manager.get_locations_with_adenoma_min_size(min_size)
        if max_size is not None:
            yield from self.manager.get_location_with_adenoma_max_size(max_size)

    @jarreader
    def get_locations_with_size(self, min_size=None, max_size=None):
        if min_size is not None:
            yield from self.manager.get_locations_with_min_size(min_size)
        if max_size is not None:
            yield from self.manager.get_location_with_max_size(max_size)

    @jarreader
    def get_histology(self, category, allow_maybe=False):
        """

        :param allow_maybe:
        :param category:
        :return: counts for category as tuple(total, proximal, distal, rectal)
        """
        return self.manager.get_histology(category, allow_maybe)

    @jarreader
    def has_dysplasia(self):
        """

        :return: True if any jar contains dysplasia
        """
        return self.manager.has_dysplasia()
