from precise_nlp.extract.cspy.base_finding import BaseFinding


class SingleFinding(BaseFinding):
    """
    Only allows a single location, and a single count
    """

    def __init__(self, location=None, removal=None, size=None, source=None):
        count = 1
        super().__init__(location, count, removal, size, source)

    def __repr__(self):
        removed = 'removed' if self.removal else ''
        return f'<{self.count}{removed}@{",".join(self.locations)}:{self.size}>'

    def __str__(self):
        return repr(self)

    @property
    def count(self):
        return 1

    def is_compatible(self, f):
        if not isinstance(f, SingleFinding):
            raise ValueError('Can only compare findings')
        return False

    def merge(self, f):
        if not isinstance(f, SingleFinding):
            raise ValueError('Can only merge findings')
        raise ValueError('SingleFinding cannot be merged.')
