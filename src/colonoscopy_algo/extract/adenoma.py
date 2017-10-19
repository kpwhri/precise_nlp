import re


def has_negation(index, text, window, negset):
    if window > 0:
        s = set(re.split('\W+', text[index:])[:window])
    else:
        s = set(re.split('\W+', text[:index + 1])[window:])
    return s & negset


def get_adenoma_status(text, window=5):
    """

    :param window:
    :param text:
    :return: 1=adenoma, 2=no adenoma
    """
    tubular_adenoma = re.compile(r'tubular\s+adenoma', re.IGNORECASE)
    adenomatous = re.compile(r'adenomatous', re.IGNORECASE)
    serrated_adenoma = re.compile(r'serrated\s+adenoma', re.IGNORECASE)
    tbv_adenoma = re.compile(r'tubulovillous\s+adenoma', re.IGNORECASE)
    adenomatoid = re.compile(r'adenomatoid', re.IGNORECASE)
    prenegation = {'no', 'hx', 'history', 'sessile'}
    specimens = [x.lower() for x in re.split(r'\W[A-Z]\)', text)]
    for pat in [tubular_adenoma, adenomatous, serrated_adenoma, tbv_adenoma, adenomatoid]:
        for spec in specimens:
            for m in pat.finditer(spec):
                if has_negation(m.start(), spec, -window, prenegation):
                    continue
                return 1
    return 0
