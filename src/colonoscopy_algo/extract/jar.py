
class Jar:

    def __init__(self):
        self.polyps = []
        self.polyp_count = MaybeCounter(1)


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

    def add(self, count=1):
        if count == 0:
            return
        elif count < 0:
            return
        self.count += count
        if self.greater_than:
            self.greater_than = False
            self.at_least = True

    def __add__(self, other):
        count = self.count + other.count
        greater_than = False
        at_least = self.at_least or self.greater_than or other.at_least or other.greater_than
        if self.greater_than and other.greater_than:
            count += 2
        elif self.greater_than or other.greater_than:
            count += 1
        return MaybeCounter(count, at_least=at_least, greater_than=greater_than)

    def __sub__(self, other):
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