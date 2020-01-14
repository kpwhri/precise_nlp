from loguru import logger

from precise_nlp.extract.cspy.base_finding import BaseFinding


class NaiveFinding(BaseFinding):

    def __init__(self, location=None, count=1, removal=None, size=None, source=None):
        super().__init__(location, count, removal, size, source)

    def is_compatible(self, f):
        if not isinstance(f, NaiveFinding):
            raise ValueError('Can only compare findings')
        if self.source == f.source:
            if f.removal and not self.removal:  # removal is last item mentioned, usually
                return False
            elif self._count and f._count and self._count != f._count:  # counts must be the same
                return False
            elif set(self.locations) != set(f.locations):
                return False
            elif self.size and f.size:
                return False
        else:  # sources not equal
            if self._count and f._count and self._count != f._count:
                return False
            elif self.removal and f.removal and self.removal != f.removal:
                return False
            elif self.locations and f.locations and set(self.locations) | set(f.locations):
                return False
            elif self.size and f.size and self.size != f.size:
                return False
        return True

    def merge(self, f):
        if not isinstance(f, NaiveFinding):
            raise ValueError('Can only merge findings')
        self._count = max(self._count, f._count)
        self.removal = self.removal or f.removal
        self._locations += f._locations
        if self.size and f.size:
            self.size = max(self.size, f.size)
        elif f.size:
            self.size = f.size
