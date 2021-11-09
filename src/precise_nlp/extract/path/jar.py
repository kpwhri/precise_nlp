from precise_nlp.const.enums import AssertionStatus
from precise_nlp.extract.path.polyp_size import PolypSize
from precise_nlp.extract.maybe_counter import MaybeCounter
from precise_nlp.extract.utils import depth_to_location, StandardTerminology


class Jar:

    def __init__(self):
        self.kinds = []
        self.polyps = []
        self.polyp_count = MaybeCounter(1)
        self.adenoma_count = MaybeCounter(0)
        self.adenoma_distal_count = MaybeCounter(0)
        self.adenoma_proximal_count = MaybeCounter(0)
        self.adenoma_rectal_count = MaybeCounter(0)
        self.adenoma_unknown_count = MaybeCounter(0)
        self.locations = []
        self.histologies = []
        self.polyp_size = []
        self.dysplasia = False
        self.depth = None
        self.sessile_serrated_adenoma_count = 0
        self.carcinomas = 0
        self.carcinoma_list = []  # (name, assertion status)
        self.carcinomas_maybe = 0
        self.carcinomas_possible = 0
        self.carcinomas_in_situ = 0
        self.carcinomas_in_situ_maybe = 0
        self.carcinomas_in_situ_possible = 0

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
        self.depth = depth
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
        self.locations += StandardTerminology.standardize_locations(locations)

    def add_location(self, location):
        self.add_locations([location])

    def add_histology(self, histology):
        self.histologies.append(StandardTerminology.histology(histology))

    def has_min_size(self, min_size):
        return self.polyp_size and sorted(self.polyp_size, reverse=True)[0].get_max_dim() >= min_size

    def has_max_size(self, max_size):
        """Complement of `has_min_size` so max_size is exclusive"""
        return self.polyp_size and sorted(self.polyp_size, reverse=True)[0].get_max_dim() < max_size

    def has_unknown_size(self):
        return not bool(self.polyp_size)

    def has_adenoma(self):
        return self.adenoma_count.gt(0) == 1

    def locations_or_none(self):
        if self.locations:
            yield from StandardTerminology.filter_colon(self.locations)
        else:
            yield None

    def add_ssa(self):
        self.sessile_serrated_adenoma_count += 1

    def add_ssp(self):
        self.sessile_serrated_adenoma_count += 1

    def add_carcinoma(self, term=None, status=AssertionStatus.UNKNOWN, in_situ=False):
        if status in {AssertionStatus.UNKNOWN, AssertionStatus.DEFINITE}:
            if in_situ:
                self.carcinomas_in_situ += 1
            else:
                self.carcinomas += 1
        elif status in {AssertionStatus.PROBABLE}:  # SEER maybe
            if in_situ:
                self.carcinomas_in_situ_maybe += 1
            else:
                self.carcinomas_maybe += 1
        elif status in {AssertionStatus.POSSIBLE, AssertionStatus.IMPROBABLE}:
            if in_situ:
                self.carcinomas_in_situ_possible += 1
            else:
                self.carcinomas_possible += 1
        self.carcinoma_list.append((term, status, in_situ))

    def is_colon(self):
        return ('colon' in self.kinds
                or len(set(self.locations)) == len(set(StandardTerminology.filter_colon(self.locations))))

    def maybe_colon(self):
        return bool(set(StandardTerminology.filter_colon(self.locations)))

    def is_distal(self):
        """
        Distal if location includes a distal_location keyword and no other locations
        Cite for locations:
            - https://www.cancer.gov/publications/dictionaries/cancer-terms/def/distal-colon
            - http://cebp.aacrjournals.org/content/17/5/1144
        Cite for distance: https://training.seer.cancer.gov/colorectal/anatomy/figure/figure1.html
        :return:
        """
        return bool(set(self.locations) and set(self.locations) <= set(StandardTerminology.DISTAL_LOCATIONS)) \
               or bool(self.depth and 16 < self.depth < 82)

    def maybe_distal(self):
        """
        Maybe distal if location includes a distal_location keyword but also has non-distal in same self
        Cite for locations:
            - https://www.cancer.gov/publications/dictionaries/cancer-terms/def/distal-colon
            - http://cebp.aacrjournals.org/content/17/5/1144
        Cite for distance: https://training.seer.cancer.gov/colorectal/anatomy/figure/figure1.html
        Proximal defn: https://www.ncbi.nlm.nih.gov/pubmedhealth/PMHT0022241/
        :param self:
        :return:
        """
        return bool(set(self.locations) & set(StandardTerminology.DISTAL_LOCATIONS))

    def is_proximal(self):
        """
        Proximal if location includes a proximal_location keyword and no other locations
        Cite for locations:
            - https://www.cancer.gov/publications/dictionaries/cancer-terms/def/distal-colon
            - http://cebp.aacrjournals.org/content/17/5/1144
        Cite for distance: https://training.seer.cancer.gov/colorectal/anatomy/figure/figure1.html
        Proximal defn: https://www.ncbi.nlm.nih.gov/pubmedhealth/PMHT0022241/
        :param self:
        :return:
        """
        return bool(set(self.locations) and set(self.locations) <= set(StandardTerminology.PROXIMAL_LOCATIONS)) \
               or bool(self.depth and self.depth > 82)

    def maybe_proximal(self):
        """
        Maybe proximal if location includes a proximal_location keyword but also has non-proximal in the same self
        Cite for locations:
            - https://www.cancer.gov/publications/dictionaries/cancer-terms/def/distal-colon
            - http://cebp.aacrjournals.org/content/17/5/1144
        Cite for distance: https://training.seer.cancer.gov/colorectal/anatomy/figure/figure1.html
        Proximal defn: https://www.ncbi.nlm.nih.gov/pubmedhealth/PMHT0022241/
        :return:
        """
        return bool(set(self.locations) & set(StandardTerminology.PROXIMAL_LOCATIONS))

    def is_rectal(self):
        """
        Rectal if location only has rectum
        Cite for distance: https://training.seer.cancer.gov/colorectal/anatomy/figure/figure1.html
            * < 17cm since 17cm is also sigmoid (being conservative)
        :param self:
        :return:
        """
        return bool(self.locations and set(self.locations) <= set(StandardTerminology.RECTAL_LOCATIONS)) \
               or bool(self.depth and 4 <= self.depth <= 16)

    def maybe_rectal(self):
        """
        Maybe rectal if location includes a 'rectum' along with other location keywords
        :param self:
        :return:
        """
        return bool(set(self.locations) & set(StandardTerminology.RECTAL_LOCATIONS))

    def add_adenoma_count(self, count=1, greater_than=False, at_least=False):
        self.adenoma_count.add(count, greater_than, at_least)
