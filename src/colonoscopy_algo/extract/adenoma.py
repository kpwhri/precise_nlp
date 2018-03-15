import re
from colonoscopy_algo.extract.jar import PathManager


def has_negation(index, text, window, negset):
    if window > 0:
        s = set(re.split('\W+', text[index:])[:window])
    else:
        s = set(re.split('\W+', text[:index + 1])[window:])
    return s & negset


def inspect(patterns, specimens, prenegation=None, postnegation=None,
            window=5, terminate_on_negation=False):
    for pat in patterns if isinstance(patterns, list) else [patterns]:
        for spec in specimens:
            if find_in_specimen(pat, spec, prenegation, postnegation,
                                window, terminate_on_negation):
                return 1
    return 0


def find_in_specimen(pattern, specimen, prenegation=None, postnegation=None,
                     window=5, terminate_on_negation=False):
    """

    :param pattern:
    :param specimen:
    :param prenegation:
    :param postnegation:
    :param window:
    :param terminate_on_negation: if any negation found for any pattern, then not found
    :return:
    """
    for m in pattern.finditer(specimen):
        if prenegation and has_negation(m.start(), specimen, -window, prenegation):
            if terminate_on_negation:
                break
            continue
        elif postnegation and has_negation(m.start(), specimen, window, postnegation):
            if terminate_on_negation:
                break
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


def get_highgrade_dysplasia(specimens):
    """
    Identify mentions of highgrade dysplasia
    :param specimens:
    :return:
    """
    dysplasia = re.compile(r'(high(\s*|-)?grade|severe)(\W*\w+)?\W+dysplas\w*', re.IGNORECASE)
    prenegation = {'no', 'without'}
    return inspect([dysplasia], specimens, prenegation=prenegation,
                   terminate_on_negation=True)


def get_adenoma_count(specimens, bins=(3,), many=7):
    """

    :param many: count for language like "many" or "lots"
    :param specimens:
    :param bins: tuple of beginning of subsequent bins,
        such that the first bin contains 0 < bins[0];
        None -> raw count
    :return:
    """
    lkp = {str(x): x for x in range(1, 10)}
    lkp.update({
        'one': 1,
        'two': 2,
        'three': 3,
        'four': 4,
        'five': 5
    })
    count = 0
    names = '|'.join(lkp.keys())
    patterns = [
        re.compile(f'polyps?\W*x\W*({names})', re.IGNORECASE),
    ]
    for specimen in specimens:
        if get_adenoma_status([specimen]):
            spec_count = 1
            for pat in patterns:
                for m in pat.finditer(specimen):
                    spec_count = lkp[m.group(1)]
                    break
                if spec_count > 1:
                    break
            count += spec_count

    # determine score
    if not bins:
        return count
    for i, cutoff in enumerate(bins):
        if count < cutoff:
            return i
    return len(bins)  # top bin


def get_adenoma_count_advanced(text, greater_than=2):
    """
    Defaulting to bin for >3
    :param text:
    :return:
    """
    pm = PathManager(text)
    count = pm.get_adenoma_count()
    print(count)
    return 1 if count.gt(greater_than) == 1 else 0


def has_large_adenoma():
    return False
