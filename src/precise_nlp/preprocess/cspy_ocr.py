import re

from loguru import logger

from precise_nlp.extract.cspy import CspyManager
from precise_nlp.extract.utils import Indication


def fix_ocr_problems(cspy_text):
    cspy = CspyManager(cspy_text)
    try:
        if new_text := column_separated_indications(cspy, cspy_text):
            return new_text
    except ValueError as e:
        logger.exception(e)
        logger.error('Issue identifying indication section.')
    return cspy_text


def column_separated_indications(cspy: CspyManager, cspy_text: str):
    """
    OCR software occasionally reads top-down before left-to-right.
     This will often results in an empty indications section, but a full findings.
    Fix this by placing the text in the correct position.
    Approach:
        1. Assume sections are newline-divided
        2. Get findings header, line-split, and match with INDICATIONS regexes
    :param cspy:
    :param cspy_text:
    :return:
    """
    ind = cspy.get_indication()
    if ind != Indication.UNKNOWN or ''.join(cspy._get_section(cspy.INDICATIONS)).strip():
        return None
    indication_match = re.search(r'indications?:', cspy_text, re.I)
    if not indication_match:
        raise ValueError(f'Missing indication section!')
    pat = re.compile('(limitations|complications)', re.I)
    for findings in list(cspy._get_section(cspy.FINDINGS)):
        if m := pat.search(findings[:100]):
            curr_index = m.start()
        else:  # use a moving 50 character window to guess where indication section is based on regexes
            curr_index = 0
            while m := cspy.get_indications_from_text_debug(findings[curr_index:curr_index + 50]):
                ind, m = m
                if not m:
                    break
                curr_index += m.end()
        if curr_index > 0:
            new_text = ' '.join((
                cspy_text[:indication_match.end()],
                findings[:curr_index],
                cspy_text[indication_match.end():]
            ))
            return new_text
