import re


def has_negation(index, text, window, negset):
    if window > 0:
        s = set(re.split('\W+', text[index:])[:window])
    else:
        s = set(re.split('\W+', text[:index + 1])[window:])
    return s & negset


def inspect(patterns, specimens, prenegation=None, postnegation=None, window=5):
    for pat in patterns if isinstance(patterns, list) else [patterns]:
        for spec in specimens:
            for m in pat.finditer(spec):
                if prenegation and has_negation(m.start(), spec, -window, prenegation):
                    continue
                elif postnegation and has_negation(m.start(), spec, window, postnegation):
                    continue
                return 1
    return 0


def get_adenoma_status(specimens, window=5):
    """

    :param specimens:
    :param window:
    :return: 1=adenoma, 2=no adenoma
    """
    tubular_adenoma = re.compile(r'tubular\s+adenoma', re.IGNORECASE)
    adenomatous = re.compile(r'adenomatous', re.IGNORECASE)
    serrated_adenoma = re.compile(r'serrated\s+adenoma', re.IGNORECASE)
    tbv_adenoma = re.compile(r'tubulovillous\s+adenoma', re.IGNORECASE)
    adenomatoid = re.compile(r'adenomatoid', re.IGNORECASE)
    prenegation = {'no', 'hx', 'history', 'sessile'}
    return inspect(
        [tubular_adenoma, adenomatous, serrated_adenoma, tbv_adenoma, adenomatoid],
        specimens,
        prenegation,
        window=window
    )


def get_adenoma_histology(specimens):
    """

    :param specimens:
    :return:
    """
    tubular = re.compile(r'tubular', re.IGNORECASE)
    tubulovillous = re.compile(r'tubulovillous', re.IGNORECASE)
    villous = re.compile(r'villous', re.IGNORECASE)
    tb = inspect(tubular, specimens)
    tbv = inspect(tubulovillous, specimens)
    vl = inspect(villous, specimens)

    return tb, int(tbv or (tb and vl)), vl
