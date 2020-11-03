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

    def add_carcinoma(self, term=None, status=AssertionStatus.UNKNOWN):
        if status in {AssertionStatus.UNKNOWN, AssertionStatus.DEFINITE}:
            self.carcinomas += 1
        elif status in {AssertionStatus.PROBABLE, AssertionStatus.POSSIBLE,
                        AssertionStatus.IMPROBABLE}:
            self.carcinomas_maybe += 1
        self.carcinoma_list.append((term, status))