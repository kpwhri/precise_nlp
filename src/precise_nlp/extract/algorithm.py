import re

from loguru import logger

from precise_nlp.extract.cspy import CspyManager
from precise_nlp.extract.cspy.cspy import FindingVersion
from precise_nlp.extract.path.path_manager import PathManager
from precise_nlp.const.enums import AdenomaCountMethod, Histology, Location


def has_negation(index, text, window, negset):
    if window > 0:
        s = set(re.split(r'\W+', text[index:])[:window])
    else:
        s = set(re.split(r'\W+', text[:index + 1])[window:])
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


def get_adenoma_histology(pm: PathManager):
    """
    Uses JarManager to identify histology
    :param pm: PathManager
    :return:
    """
    tub = pm.get_histology(Histology.TUBULAR)
    tbv = pm.get_histology(Histology.TUBULOVILLOUS)
    vil = pm.get_histology(Histology.VILLOUS)
    return tub[0], tbv[0], vil[0]


def get_villous_histology(pm: PathManager,
                          location: Location = Location.ANY,
                          allow_maybe=False):
    """
    Get villous or tubulovillous by requested location
    :param allow_maybe: if False, only include when location is guaranteed
    :param location: location to look for
    :param pm:
    :return:
    """
    tbv = pm.get_histology(Histology.TUBULOVILLOUS, allow_maybe=allow_maybe)
    vil = pm.get_histology(Histology.VILLOUS, allow_maybe=allow_maybe)
    if location == Location.ANY:
        return 1 if tbv[0] + vil[0] else 0
    elif location == Location.PROXIMAL:
        return 1 if tbv[1] + vil[1] else 0
    elif location == Location.DISTAL:
        return 1 if tbv[2] + vil[2] else 0
    elif location == Location.RECTAL:
        return 1 if tbv[3] + vil[3] else 0
    elif location == Location.UNKNOWN:
        return 1 if tbv[4] + vil[4] else 0
    else:
        raise ValueError(f'Unrecognized location: {location}')


def get_adenoma_histology_simple(specimens):
    """
    Uses a simple set of negation and terms to identify tubular, tubulovillous, and villous histology for colons.
    :param specimens:
    :return:
    """
    tubular = re.compile(r'tubular', re.IGNORECASE)
    tubulovillous = re.compile(r'tubulovillous', re.IGNORECASE)
    villous = re.compile(r'(?<!tubulo)villous', re.IGNORECASE)
    exclusion = re.compile(r'^(\W*\w+){0,4}\W*(bowel|stomach|gastric|(duoden|ile)(al|um))', re.IGNORECASE)
    tb, tbv, vl = 0, 0, 0
    for specimen in specimens:
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
    prenegation = {'no', 'without', 'negative'}
    return inspect([dysplasia], specimens, prenegation=prenegation,
                   terminate_on_negation=True)


def get_dysplasia(pm: PathManager):
    return pm.get_dysplasia()


def has_dysplasia(pm: PathManager):
    """
    Identify mentions of highgrade dysplasia
    :param pm:
    :return:
    """
    return 1 if pm.has_dysplasia() else 0


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
        re.compile(fr'polyps?\W*x\W*({names})', re.IGNORECASE),
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


def _get_adenoma_count(func, greater_than, jar_count):
    if jar_count:
        count = func(AdenomaCountMethod.ONE_PER_JAR)
    else:
        count = func(AdenomaCountMethod.COUNT_IN_JAR)
    return (
        1 if count.gt(greater_than) == 1 else 0,
        0 if count.eq(0) == 1 else 1,
        count
    )


def get_adenoma_count_advanced(pm: PathManager, greater_than=2, jar_count=False):
    """
    Defaulting to bin for >3
    :param pm: PathManager instance
    :return:
    """
    return _get_adenoma_count(pm.get_adenoma_count, greater_than, jar_count)


def get_adenoma_distal(pm: PathManager, greater_than=2, jar_count=False):
    """

    :param pm:
    :return:
    """
    return _get_adenoma_count(pm.get_adenoma_distal_count, greater_than, jar_count)


def get_adenoma_proximal(pm: PathManager, greater_than=2, jar_count=False):
    """

    :param pm:
    :return:
    """
    return _get_adenoma_count(pm.get_adenoma_proximal_count, greater_than, jar_count)


def get_adenoma_rectal(pm: PathManager, greater_than=2, jar_count=False):
    """

    :param pm:
    :return:
    """
    return _get_adenoma_count(pm.get_adenoma_rectal_count, greater_than, jar_count)


def get_adenoma_unknown(pm: PathManager, greater_than=2, jar_count=False):
    """

    :param pm:
    :return:
    """
    return _get_adenoma_count(pm.get_adenoma_unknown_count, greater_than, jar_count)


def has_large_adenoma(pm: PathManager, cm: CspyManager, *, min_size=10, version=FindingVersion.PRECISE):
    if version == FindingVersion.BROAD:
        return has_large_adenoma_broad(pm, cm, min_size)
    elif version == FindingVersion.PRECISE:
        return has_large_adenoma_precise(pm, cm, min_size)
    else:
        raise ValueError(f'Unexpected version: {version}')


def has_large_adenoma_broad(pm: PathManager, cm: CspyManager, min_size=10):
    """
    Location has large polyp and an adenoma
    :param pm:
    :param cm:
    :param min_size:
    :return:
    """
    s = set(pm.get_locations_with_adenoma())
    s2 = set(pm.get_locations_with_size(min_size))
    for f in cm.get_findings_of_size(min_size):
        if not f.locations:
            s2.add(None)
        for loc in f.locations:
            s2.add(loc)
    logger.info(f'Adenoma locations: {[str(ss) for ss in s]}')
    logger.info(f'Large polyp locations: {s2}')
    return 1 if (s & s2  # both contain same location
                 or s2 and None in s  # unknown adenoma location and large polyp in cspy
                 or s and None in s2  # unknown large polyp location (cspy)
                 ) else 0


def has_large_adenoma_precise(pm: PathManager, cm: CspyManager, min_size=10):
    """
    Adds option of 'maybe'

    WARNING: Logic will break down if >= 3 jars with the same location
    :param pm:
    :param cm:
    :param min_size:
    :return: 1=large adenoma, 0=no large adenoma, 9=maybe large adenoma
    """
    if len(list(pm.get_locations_with_large_adenoma())) > 0:
        logger.info('Found size and adenoma-ness in pathology')
        return 1  # early exit: we found size and adenoma-ness
    path_adenoma = list(pm.get_locations_with_unknown_adenoma_size())
    # if not path_adenoma:
    #     return 0  # early exit: no adenomas
    path_small = list(pm.get_locations_with_adenoma_size(max_size=min_size))
    # NOTE: small adenoma not reliable due to fragments
    path_adenoma += path_small
    cspy_large = list()
    cspy_small = list()
    for f in cm.get_findings():
        if f.size >= min_size:
            for loc in f.locations_or_none():
                cspy_large.append(loc)
        else:
            for loc in f.locations_or_none():
                cspy_small.append(loc)
    logger.info(f'Adenoma locations: {[str(ss) for ss in path_adenoma]}')
    logger.info(f'Large polyp locations: {cspy_large}')

    if not cspy_large:
        return 0  # no large polyp

    has_maybe = False
    for aden_loc in path_adenoma:
        if aden_loc in cspy_large:  # is large adenoma
            if aden_loc in cspy_small:  # might be small
                ## NOTE: small path is unreliable
                # if aden_loc in path_small:  # here's the small one
                #     return 1
                # else:
                # if path_adenoma.count(aden_loc) == 1:
                #     return 1
                if path_adenoma.count(aden_loc) < cspy_large.count(aden_loc) + cspy_small.count(aden_loc):
                    has_maybe = True
                else:
                    return 1
            else:
                return 1
    return 9 if has_maybe else 0


def get_sessile_serrated_adenoma(pm: PathManager, jar_count=True):
    return pm.get_sessile_serrated_count(jar_count=jar_count)


def get_carcinomas(pm: PathManager, jar_count=True):
    return pm.get_carcinoma_count(jar_count=jar_count)


def get_carcinomas_maybe(pm: PathManager, jar_count=True):
    return pm.get_carcinoma_maybe_count(jar_count=jar_count, probable_only=True)


def get_carcinomas_possible(pm: PathManager, jar_count=True):
    return pm.get_carcinoma_maybe_count(jar_count=jar_count)


def get_carcinomas_in_situ(pm: PathManager, jar_count=True):
    return pm.get_carcinoma_in_situ_count(jar_count=jar_count)


def get_carcinomas_in_situ_maybe(pm: PathManager, jar_count=True):
    return pm.get_carcinoma_in_situ_maybe_count(jar_count=jar_count, probable_only=True)


def get_carcinomas_in_situ_possible(pm: PathManager, jar_count=True):
    return pm.get_carcinoma_in_situ_maybe_count(jar_count=jar_count)
