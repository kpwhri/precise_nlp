import re

from regexify.pattern import Pattern

from precise_nlp.extract.utils import ColonPrep

NUMBER_PATTERN = re.compile(r'(\d{1,3}(?:\.\d{,2})?)', re.IGNORECASE)
DEPTH_PATTERN = re.compile(r'(\d{1,3}(?:\.\d{,2})?)\W*[cm]m', re.IGNORECASE)
# this should probably take the larger of the two options
# instead of ignoring the second
SIZE_PATTERN = re.compile(
    r'(?P<n1><?\d{1,3}(?:\.\d)?)'
    r'(?:\W*(?:[cm]m))?'
    r'(?:\W*(x|to|-|and)\W*'
    r'(?P<n2>\d{1,3}(?:\.\d)?))?'
    r'\W*(?P<m>[cm]m)',
    re.IGNORECASE
)
IN_SIZE_PATTERN = re.compile(
    r'(?:(?P<n1>\d{1,3}(?:\.\d)?)\W*(?:[cm]m)?\W*'
    r'(?:to|x|-|and)\W*)?'
    r'(?P<n2>[<>]?\d{1,3}(?:\.\d)?)\W*(?P<m>[cm]m)\W*in\W*size',
    re.IGNORECASE
)
AT_DEPTH_PATTERN = re.compile(
    r'(?<!\d\W)(?<!\d\W\W)(?<![cm]m\W)(?:at|@|to|from)'
    r'\W*(\d{1,3}(?:\.\d)?)\W*[cm]m(\W*(proximal\W*)?(from|to)\W*(the\W*)?an(al|us))?',
    re.IGNORECASE)
CM_DEPTH_PATTERN = re.compile(r'(\d{2,3})\W*cm(\W*(proximal\W*)?(from|to)\W*(the\W*)?an(al|us))?', re.IGNORECASE)
SSPLIT = re.compile(r'\.(?=\s)')
NO_PERIOD_SENT = re.compile(r'\n\W*[A-Z0-9]')  # no ignorecase!

PROCEDURE_EXTENT_COMPLETE = Pattern(
    r'('
    r'extent of procedure ((the )?colon )?cecum|term\w* ileum'
    r'|(cecal location|cecum|append\w* orifice) ((was|were) )?(identified|reached)'
    r'|to (the )?(\w+ )?cecum'
    r'|advanced into the final \d{1,2} cm of the term\w* ileum'
    r')'
)
PROCEDURE_EXTENT_INCOMPLETE = Pattern(
    r'('
    r'extent of procedure'
    r')'
)
COLON_PREP_PRE = Pattern(
    r'(((colon|bowel) )?prep\w+ (visualization )?(was )?(very )?(?P<prep>{})\w*)'.format(ColonPrep.REGEX)
)
COLON_PREP_POST = Pattern(r'((?P<prep>{})\w*) (\w+ ){{0,2}}prepared colon'.format(ColonPrep.REGEX))

isayo = r'\Wis\W*a\W*\d{2,3}\W*year\W*old'
screen = r'(for|cancer)? screening'
occult = r'positive\W*((hem)?[aeo]{1,2}cc?ult|fit\b|g?fobt)'
occult2 = r'(hem[aeo]{1,2}(cc?ult)?|\bfit) positive'
occult3 = r'\bfit\W*stool\b'  # no mention of positive (might be over-specific)
abnormal = r'abnormal'
blood = r'blood|bleed|brb|hematochezia|melena|tarry'
anemia = r'anemi(a|c)'
diarrhea = r'diarr?h\w+|loose|watery'
constip = r'constipat'
change1 = r'urgency|incontin|muco?us|irregular'
change2 = r'altered\s*bowel|\bchange(s|d)?\W*(?:\w+\W*){0,2}?bowel\b'
ibs = r'(\bibs\b|irritable)'
mass = r'mass'
pain = r'(?<!chest\s)pain(?!less)'
weight = r'(weight|wt)\W*loss|anorexi'
mets = r'metasta'
suspect = r'suspect'
colitis = r'colitis'
# divertic = r'divertic'  # removed from diagnostic for internal inconsistency
perhx = r'(?<!family\W)(?<!family)(((h[ist]+ory|hx)\W*of)|h\/o)'
personal_history = r'personal history'
famhx = r'family|famhx|mother|father|parent|sister|brother|son|daughter|\bFH\b'
genetic = r'fap|lynch|hnpcc'
followup = r'follow\W*-?\W*up|self\/u'
polyps = r'polyps'  # for SURVEILLANCE with negation?
ibd = r'(ibd|\buc\b|ulcerative|crohn|inflammatory bowl pan colitis)'
surveil = r'(surveillance|barrett)'
INDICATION_DIAGNOSTIC = Pattern(f'({occult}|{occult2}|{occult3}|{abnormal}|{blood}|{anemia}|{diarrhea}'
                                f'|{constip}|{change1}|{change2}|{ibs}|{mass}'
                                f'|{pain}|{weight}|{mets}|{suspect})',
                                negates=[r'\bno\b'])
INDICATION_SURVEILLANCE = Pattern(f'({ibd}|{perhx}|{genetic}|{followup}'
                                  f'|{surveil}|{personal_history})',
                                  negates=[r'\bno\b'])
INDICATION_SCREENING = Pattern(f'({screen}|{famhx})',
                               negates=[r'\bno\b'])
