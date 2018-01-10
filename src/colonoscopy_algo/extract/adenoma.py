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
            if find_in_specimen(pat, spec, prenegation, postnegation, window):
                return 1
    return 0


def find_in_specimen(pattern, specimen, prenegation=None, postnegation=None, window=5):
    for m in pattern.finditer(specimen):
        if prenegation and has_negation(m.start(), specimen, -window, prenegation):
            continue
        elif postnegation and has_negation(m.start(), specimen, window, postnegation):
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
    villous = re.compile(r'(?<!tubulo)villous', re.IGNORECASE)
    exclusion = re.compile(r'^(\W*\w+){0,4}\W*(bowel|stomach|gastric|(duoden|ile)(al|um))', re.IGNORECASE)
    tb, tbv, vl = 0, 0, 0
    for specimen in specimens:
        # print('>> ', specimen)
        if not find_in_specimen(re.compile('colon'), specimen) and find_in_specimen(exclusion, specimen):
            continue
        tb_ = find_in_specimen(tubular, specimen)
        tbv_ = find_in_specimen(tubulovillous, specimen)
        vl_ = find_in_specimen(villous, specimen, prenegation={'no'})

        tb = tb or tb_
        vl = vl or vl_
        tbv = int(tbv or tbv_ or (tb_ and vl_))
    return tb, tbv, vl
