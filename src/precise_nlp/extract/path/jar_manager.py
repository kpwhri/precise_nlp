from loguru import logger

from precise_nlp.const import patterns
from precise_nlp.const.enums import AssertionStatus, AdenomaCountMethod, Histology
from precise_nlp.extract.path import terms
from precise_nlp.extract.path.jar import Jar
from precise_nlp.extract.path.polyp_size import PolypSize
from precise_nlp.extract.maybe_counter import MaybeCounter
from precise_nlp.extract.path.path_section import PathSection
from precise_nlp.extract.utils import StandardTerminology


class JarManager:
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
    ADENOMA_NEGATION = {'no', 'history', 'hx', 'sessile', 'without', 'r/o', 'negative'}
    ADENOMA_NEGATION_WITHOUT_SESSILE = ADENOMA_NEGATION - {'sessile'}
    HISTOLOGY_NEGATION = {'no', 'or'}
    HISTOLOGY_NEGATION_MOD = {'evidence', 'residual'}
    NUMBER = {'one', 'two', 'three', 'four', 'five', 'six',
              'seven', 'eight', 'nine'} | {str(i) for i in range(10)}
    NUMBER_CONVERT = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    }
    NUMBER_CONVERT.update({str(i): i for i in range(10)})

    DYSPLASIA = {'dysplasia', 'dysplastic'}
    HIGHGRADE_DYS = {'highgrade', 'grade', 'severe'}

    def __init__(self):
        self.jars = []
        self.curr_jar = None

    def _adenoma_negated(self, section, allow_sessile=False):
        """
        Handle negation cases when looking specifically at adenoma.
        :param section:
        :return:
        """
        negation = self.ADENOMA_NEGATION_WITHOUT_SESSILE if allow_sessile else self.ADENOMA_NEGATION
        if section.has_before(negation
                              ) and not section.has_before(StandardTerminology.HISTOLOGY, window=4):
            return True
        elif section.has_before('or', window=3) and section.has_before(negation, window=7):
            return True
        elif section.has_before(['no', 'without'], window=5) and section.has_before(['evidence', 'hx', 'history'],
                                                                                    window=4):
            return True
        elif section.has_before('r', window=5) and section.has_before('o', window=4):
            return True
        elif section.has_before('negative', window=8) and section.has_before('for', window=7):
            return True
        elif section.has_before('or', window=3) and section.has_before('negative', window=10) \
                and section.has_before('for', window=9):
            return True

        elif section.has_after(['not', 'none', 'no'], window=2):
            return True
        return False

    def _histology_negated(self, section):
        if section.has_before(self.HISTOLOGY_NEGATION,
                              window=1) and not section.has_after(self.ADENOMA + self.ADENOMAS, window=3):
            return True
        elif section.has_before(self.HISTOLOGY_NEGATION,
                                window=5) and section.has_before(self.HISTOLOGY_NEGATION_MOD, window=4):
            return True
        return False

    def _is_sessile_serrated(self, section):
        if section.has_before('sessile', window=3) and section.has_before('serrated', window=2):
            return True
        return False

    def cursory_diagnosis_examination(self, section):
        jar = Jar()
        section = PathSection(section)
        found_polyp = False
        for word in section:
            if word.isin(StandardTerminology.LOCATIONS):
                if (word.isin(StandardTerminology.SPECIFYING_LOCATIONS)
                        and section.has_after(StandardTerminology.LOCATIONS, window=3)):
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
                num = float(word.match(patterns.NUMBER_PATTERN)) / 10
                if num < 10:
                    if section.has_after(['dimension', 'maximal', 'maximum'], window=4):
                        # might be polyp dimensions
                        jar.set_polyp_size(num, cm=True)
                else:
                    jar.set_depth(num)

            elif word.isin(self.POLYPS):  # polyps/biopsies
                if self._is_sessile_serrated(section):
                    if not section.has_before(self.ADENOMA_NEGATION_WITHOUT_SESSILE):
                        jar.add_ssp()
                    continue
                elif found_polyp or section.has_before(self.ADENOMA_NEGATION):
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
                    (word.isin(self.ADENOMA) and section.has_after(self.POLYPS, window=1)) or
                    (word.isin(self.ADENOMA) and jar.polyp_count.gt(1) == 1)
            ):
                if self._adenoma_negated(section, allow_sessile=True):
                    continue
                if self._is_sessile_serrated(section):
                    jar.add_ssa()
                    continue
                num = section.has_after(self.NUMBER, window=2)
                has_frags = section.has_before(self.FRAGMENTS, window=4)
                one_polyp = section.has_after(self.POLYP, window=1)
                if num and not num.spl.startswith(')') and not num == '1':
                    # `not num == 1` will allow 'tubular adenoma 1 of 5 fragments
                    if section.has_after(self.FRAGMENTS, window=4):
                        num = False
                if not num:
                    num = section.has_before(self.NUMBER, window=5)
                if section.has_before(self.FRAGMENT, window=4):
                    jar.add_adenoma_count(1)
                if num and has_frags:
                    jar.add_adenoma_count(1, at_least=True)
                elif num:  # identified number
                    jar.add_adenoma_count(self.NUMBER_CONVERT[str(num)])
                elif one_polyp:
                    jar.add_adenoma_count(1)
                elif word.isin(self.ADENOMA) and jar.polyp_count.gt(1) == 1:
                    jar.add_adenoma_count(1, at_least=True)
                else:  # default case
                    jar.add_adenoma_count(1, greater_than=True)

            elif word.isin(self.ADENOMA):
                if not self._adenoma_negated(section, allow_sessile=True):
                    if self._is_sessile_serrated(section):
                        jar.add_ssa()
                    elif section.has_before(self.FRAGMENTS, window=4):
                        jar.add_adenoma_count(1, at_least=True)
                    else:
                        jar.add_adenoma_count(1)

            elif word.isin(self.COLON):
                jar.kinds.append('colon')

            elif word.isin(StandardTerminology.HISTOLOGY.keys()):
                if self._histology_negated(section):
                    continue
                jar.add_histology(word)

            elif word.isin(self.DYSPLASIA):
                if section.has_before(self.HIGHGRADE_DYS, window=2):
                    if section.has_before('no', window=5) and section.has_before('evidence', window=4):
                        jar.add_dysplasia(negative=1)
                        pass  # don't make false in case something else
                    elif section.has_before({'no', 'without', 'low', 'negative'}, window=4):
                        jar.add_dysplasia(negative=1)
                    else:
                        jar.add_dysplasia(positive=1)

            # ssp/ssa
            elif word.isin({'ssp', 'ssps'}):
                jar.add_ssp()
            elif word.isin({'ssa', 'ssas'}):
                jar.add_ssa()

            # carcinoma
            elif self.is_cancer(word, section):
                is_in_situ = False
                i = 0
                for i, prev_word in enumerate(section.iter_prev_words()):
                    if prev_word.isin(terms.OTHER_CANCER_TERMS):
                        continue
                    elif prev_word.isin({  # stopwords
                        '&', 'and', '/',
                        'in',  # 'in' is included for 'in situ'
                    }):
                        continue
                    elif prev_word.isin({
                        'situ', 'in-situ',
                    }):
                        is_in_situ = True
                    else:
                        break
                in_situ_incr = 0
                if w := section.has_after({'situ', 'in-situ'}, window=2):
                    is_in_situ = True
                    in_situ_incr = w.index - section.curr
                carcinoma = ' '.join(str(w) for w in section[section.curr - i: section.curr + 1 + in_situ_incr])
                if section.has_before(terms.CANCER_SEER_MAYBE, window=i + 3, offset=i):
                    # enough of a window to skip an 'of', 'for', or 'with'
                    jar.add_carcinoma(carcinoma, AssertionStatus.PROBABLE, in_situ=is_in_situ)
                elif section.has_before(terms.CANCER_NEGATION_TERMS, window=i + 3, offset=i):
                    jar.add_carcinoma(carcinoma, AssertionStatus.NEGATED, in_situ=is_in_situ)
                elif section.has_before(terms.CANCER_MAYBE_TERMS, window=i + 3, offset=i):
                    jar.add_carcinoma(carcinoma, AssertionStatus.POSSIBLE, in_situ=is_in_situ)
                else:
                    jar.add_carcinoma(carcinoma, AssertionStatus.DEFINITE, in_situ=is_in_situ)

        logger.info('Adenoma Count for Jar: {}'.format(jar.adenoma_count))
        self.jars.append(jar)
        self.curr_jar = len(self.jars) - 1
        return self

    def is_cancer(self, word, section):
        if word.isin({
            'carcinoma', 'carcinomas',
            'adenocarcinoma', 'adenocarcinomas',
            'adenoca', 'adenocas',
            'cystadenocarcinoma', 'cystadenocarcinomas',
            'melanoma', 'melanomas',  # TODO: only in rectum
        }):
            return True
        elif word.endswith('sarcoma', 'sarcomas', 'fibroma', 'fibromas'):
            return True
        elif word.isin({'neoplasm', 'neoplasms',
                        'myoepithelioma', 'myoepitheliomas',
                        'epithelioma', 'epitheliomas'}):
            if section.has_before({'malignant'}, window=3):
                return True
        elif word.isin({'tumor', 'tumors'}):
            if section.has_before({
                'adenomatoid', 'adenomatoidal',
                'carcinoid', 'carcinoidal', 'cell',
            }):
                return True
            if section.has_before({'malignant'}, window=3):
                return True

    def get_current_jar(self):
        if self.curr_jar is not None:
            return self.jars[self.curr_jar]
        raise ValueError('No current jar')

    def postprocess(self, allow_maybe=False):
        """
        Post-processing steps to assign locations to various components, etc.
        :return:
        """
        for jar in self.jars:
            counts = []
            # distal
            if jar.is_distal():
                jar.adenoma_distal_count = jar.adenoma_count
            elif allow_maybe and jar.maybe_distal():  # be conservative
                if jar.adenoma_count:
                    jar.adenoma_distal_count.add(0, at_least=True)
            else:
                counts.append(0)
            # proximal
            if jar.is_proximal():
                jar.adenoma_proximal_count = jar.adenoma_count
            elif allow_maybe and jar.maybe_proximal():  # be conservative
                if jar.adenoma_count:
                    jar.adenoma_proximal_count.add(0, at_least=True)
            else:
                counts.append(0)
            # rectal
            if jar.is_rectal():
                jar.adenoma_rectal_count = jar.adenoma_count
            elif allow_maybe and jar.maybe_rectal():  # be conservative
                if jar.adenoma_count:
                    jar.adenoma_rectal_count.add(0, at_least=True)
            else:
                counts.append(0)
            # unknown
            if len(counts) == 3:  # no location identified
                jar.adenoma_unknown_count = jar.adenoma_count

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

    def get_adenoma_rectal_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        """

        :param method: AdenomaCountMethod - per jar or total number
        :return:
        """
        count = MaybeCounter(0)
        for jar in self.jars:
            if method == AdenomaCountMethod.COUNT_IN_JAR:
                count += jar.adenoma_rectal_count
            elif method == AdenomaCountMethod.ONE_PER_JAR:
                count += 1 if jar.adenoma_rectal_count else 0
        return count

    def get_adenoma_unknown_count(self, method=AdenomaCountMethod.COUNT_IN_JAR):
        """

        :param method: AdenomaCountMethod - per jar or total number
        :return:
        """
        count = MaybeCounter(0)
        for jar in self.jars:
            if method == AdenomaCountMethod.COUNT_IN_JAR:
                count += jar.adenoma_unknown_count
            elif method == AdenomaCountMethod.ONE_PER_JAR:
                count += 1 if jar.adenoma_unknown_count else 0
        return count

    def get_locations_with_large_adenoma(self, min_size=10):
        """
        All locations with a large adenoma using pathology report only
        :return:
        """
        for jar in self.jars:
            if jar.has_adenoma() and jar.has_min_size(min_size):
                yield from jar.locations_or_none()

    def get_locations_with_unknown_adenoma_size(self):
        """
        All locations with adenoma and size is unknown (based on pathology report)
        :return:
        """
        for jar in self.jars:
            if jar.has_adenoma() and jar.has_unknown_size():
                yield from jar.locations_or_none()

    def get_locations_with_adenoma(self):
        for jar in self.jars:
            if jar.has_adenoma():
                yield from jar.locations_or_none()

    def get_locations_with_min_size(self, min_size):
        for jar in self.jars:
            if jar.has_min_size(min_size):
                yield from jar.locations_or_none()

    def get_location_with_max_size(self, max_size):
        """
        Strictly less than (not equal to) max_size to be complement of `get_locations_with_min_size`
        :param max_size:
        :return:
        """
        for jar in self.jars:
            if jar.has_max_size(max_size):
                yield from jar.locations_or_none()

    def get_locations_with_adenoma_min_size(self, min_size):
        for jar in self.jars:
            if jar.has_adenoma() and jar.has_min_size(min_size):
                yield from jar.locations_or_none()

    def get_location_with_adenoma_max_size(self, max_size):
        """
        Strictly less than (not equal to) max_size to be complement of `get_locations_with_min_size`
        :param max_size:
        :return:
        """
        for jar in self.jars:
            if jar.has_adenoma() and jar.has_max_size(max_size):
                yield from jar.locations_or_none()

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
        if jar.locations:  # if jar already has locations
            return
        section = PathSection(section)
        for word in section:
            if word.isin(StandardTerminology.LOCATIONS):
                if (word.isin(StandardTerminology.SPECIFYING_LOCATIONS)
                        and section.has_after(StandardTerminology.LOCATIONS, window=3)):
                    continue  # distal is descriptive of another location (e.g., distal transverse)
                jar.add_location(word)
            elif word.matches(patterns.DEPTH_PATTERN) and 'cm' in word.word \
                    or word.matches(patterns.NUMBER_PATTERN) \
                    and section.has_after(['cm'], window=1):
                # 15 cm, etc.
                num = float(word.match(patterns.NUMBER_PATTERN))
                if num < 10:
                    pass  # not primary section
                else:  # must be >= 10cm
                    jar.set_depth(num)

    def check_dysplasia(self, section):
        jar = self.get_current_jar()
        if jar.dysplasia:
            return
        section = PathSection(section)
        for word in section:
            if word.isin(self.DYSPLASIA):
                if section.has_before(self.HIGHGRADE_DYS, window=2):
                    if section.has_before('no', window=5) and section.has_before('evidence', window=4):
                        pass  # don't make false in case something else
                    elif not section.has_before({'no', 'without', 'low'}, window=3):
                        jar.dysplasia = True
                        return

    def get_histology(self, category: Histology, allow_maybe=False):
        """

        :param allow_maybe: if True, any histology which _might_ be in that location is assumed
            to be in that location
        :param category:
        :return: counts for category as tuple(total, proximal, distal, rectal)
        """
        total = 0
        distal = 0
        proximal = 0
        rectal = 0
        unknown = 0
        for jar in self.jars:
            if not jar.is_colon():
                continue
            if category in jar.histologies:
                counts = []
                total += 1
                if jar.is_proximal():
                    proximal += 1
                elif allow_maybe and jar.maybe_proximal():
                    proximal += 1
                else:
                    counts.append(0)

                if jar.is_distal():
                    distal += 1
                elif allow_maybe and jar.maybe_distal():
                    distal += 1
                else:
                    counts.append(0)

                if jar.is_rectal():
                    rectal += 1
                elif allow_maybe and jar.maybe_rectal():
                    rectal += 1
                else:
                    counts.append(0)

                # unknown
                if len(counts) == 3:  # no location identified
                    unknown += 1
        return total, proximal, distal, rectal, unknown

    def get_any_dysplasia(self):
        has_negative = False
        for jar in self.jars:
            if jar.dysplasia.positive > 0:
                return 1
            elif jar.dysplasia.negative > 0:
                has_negative = True
        if has_negative:
            return 0
        return 99

    def has_dysplasia(self):
        for jar in self.jars:
            if jar.dysplasia.positive > 0:
                return True
        return False

    def get_sessile_serrated_count(self, jar_count=True):
        if not jar_count:
            raise NotImplementedError('jar_count is False')
        count = 0
        for jar in self.jars:
            if jar.sessile_serrated_adenoma_count > 0:
                count += 1
        return count

    def get_carcinoma_count(self, jar_count=True):
        if not jar_count:
            raise NotImplementedError('jar_count is False')
        count = 0
        for jar in self.jars:
            if jar.is_colon() and jar.carcinomas > 0 and self.not_only_colonic_melanoma(jar):
                count += 1
        return count

    def get_carcinoma_maybe_count(self, jar_count=True, probable_only=False):
        if not jar_count:
            raise NotImplementedError('jar_count is False')
        count = 0
        for jar in self.jars:
            if not jar.is_colon() or not self.not_only_colonic_melanoma(jar):
                continue
            if jar.carcinomas_maybe:
                count += 1
            elif not probable_only and jar.carcinomas_possible > 0:
                count += 1
        return count

    def get_carcinoma_in_situ_count(self, jar_count=True):
        if not jar_count:
            raise NotImplementedError('jar_count is False')
        count = 0
        for jar in self.jars:
            if jar.is_colon() and jar.carcinomas_in_situ > 0 and self.not_only_colonic_melanoma(jar):
                count += 1
        return count

    def get_carcinoma_in_situ_maybe_count(self, jar_count=True, probable_only=False):
        if not jar_count:
            raise NotImplementedError('jar_count is False')
        count = 0
        for jar in self.jars:
            if not jar.is_colon() or not self.not_only_colonic_melanoma(jar):
                continue
            if jar.carcinomas_in_situ_maybe > 0:
                count += 1
            elif not probable_only and jar.carcinomas_in_situ_possible > 0:
                count += 1
        return count

    def not_only_colonic_melanoma(self, jar: Jar):
        """
        Disallow sarcoma in the colon, only allow in rectum
        TODO: How to handle rectosigmoid?
        """
        if jar.is_rectal():
            return True
        for cancer, status, in_situ in jar.carcinoma_list:
            if 'melanoma' not in cancer:
                return True
        return False
