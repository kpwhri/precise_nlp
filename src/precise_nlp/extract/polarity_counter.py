

class PolarityCounter:

    def __init__(self, *, positive=0, negative=0):
        self.positive = positive
        self.negative = negative

    @property
    def unknown(self):
        return self.positive + self.negative == 0

    def add(self, *, positive=0, negative=0):
        self.positive += positive
        self.negative += negative

    def __add__(self, other):
        if not isinstance(other, PolarityCounter):
            return NotImplemented
        return PolarityCounter(
            positive=self.positive + other.positive,
            negative=self.negative + other.negative
        )

    def __eq__(self, other):
        return self.positive == other.positive and self.negative == other.negative
