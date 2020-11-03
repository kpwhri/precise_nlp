import re


class PolypSize:
    """
    Captures and parses the size

    Exposes a PATTERN that can be used to iterate through found items
    """

    _COUNT = r'a|an|one|two|three|four|five|six|seven|eight|nine|\d'
    _TYPE = r'(cm|mm)?'
    _MEASURE = r'\d{1,2}\.?\d{,2}'
    PATTERN = re.compile(fr'(?P<count>{_COUNT})?\W*'  # number
                         fr'(?:(?P<min1>{_MEASURE})\W*{_TYPE}'  # min size (or only size)
                         fr'(?:\W*x\W*(?P<min2>{_MEASURE})\W*{_TYPE}'
                         fr'(?:\W*x\W*(?P<min3>{_MEASURE})\W*{_TYPE})?)?)'
                         fr'(?:(?:up\W*to|to|-|and)\W*'
                         fr'(?P<max1>{_MEASURE})\W*{_TYPE}'  # max size if exists
                         fr'(?:\W*x\W*(?P<max2>{_MEASURE})\W*{_TYPE}'
                         fr'(?:\W*x\W*(?P<max3>{_MEASURE})\W*{_TYPE})?)?)?')

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