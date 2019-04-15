import re

from cronkd.util.regex import Pattern

from colonoscopy_algo.extract.utils import ColonPrep

NUMBER_PATTERN = re.compile(r'(\d{1,3}(?:\.\d{,2})?)', re.IGNORECASE)
DEPTH_PATTERN = re.compile(r'(\d{1,3}(?:\.\d{,2})?)\W*[cm]m', re.IGNORECASE)
# this should probably take the larger of the two options
# instead of ignoring the second
SIZE_PATTERN = re.compile(r'(<?\d{1,3}(?:\.\d)?)(?:\W*x\W*(?:\d{1,3}(?:\.\d)?))?\W*[cm]m', re.IGNORECASE)
AT_DEPTH_PATTERN = re.compile(r'(?:at|@|to|from)\W*(\d{1,3}(?:\.\d)?)\W*[cm]m', re.IGNORECASE)
CM_DEPTH_PATTERN = re.compile(r'(\d{2,3})\W*cm', re.IGNORECASE)
SSPLIT = re.compile(r'\.(?=\s)')
NO_PERIOD_SENT = re.compile(r'\n\W*[A-Z0-9]')  # no ignorecase!

PROCEDURE_EXTENT = Pattern(r'('
                           r'extent of procedure ((the )?colon )?cecum|term\w* ileum'
                           r'|(cecal location|cecum) was identified'
                           r'|to (the )?cecum'
                           r'|advanced into the final \d{1,2} cm of the term\w* ileum'
                           r')')
COLON_PREP_PRE = Pattern(r'(colon prep\w+ (visualization was)? (?P<prep>{})\w*)'.format(ColonPrep.REGEX))
COLON_PREP_POST = Pattern(r'((?P<prep>{})\w*) (\w+ ){{0,2}}prepared colon'.format(ColonPrep.REGEX))

ind = r'indications?:'
isayo = r'\W*is\W*a\W*\d{2,3}\W*year\W*old'
screen = r'(for|cancer)? screening'
occult = r'positive\W*((hema?)?occult|\bfit\b|g?fobt)'
abnormal = r'abnormal'
blood = r'blood|bleed|brb|hematochezia|melena|tarry'
anemia = r'anemi(a|c)'
diarrhea = r'diarrho?ea|loose|watery'
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
divertic = r'divertic'
perhx = r'(?<!family\w)(?<!family)(((h[ist]+ory|hx)\W*of)|h\/o)'
famhx = r'family|famhx|mother|father|sister|brother|\bFH\b'
genetic = r'fap|lynch|hnpcc'
followup = r'follow\W*-?\W*up|f\/u'
ibd = r'(ibd|uc|ulcerative|crohn|inflammatory bowl pan colitis)'
surveil = r'(surveillance|barrett)'
INDICATION_DIAGNOSTIC = Pattern(f'({occult}|{abnormal}|{blood}|{anemia}|{diarrhea}'
                                f'|{constip}|{change1}|{change2}|{ibs}|{mass}'
                                f'|{mass}|{pain}|{weight}|{mets}|{suspect}|{divertic})')
INDICATION_SURVEILLANCE = Pattern(f'({ibd}|{perhx}|{genetic}|{followup}'
                                  f'|{surveil})')
INDICATION_SCREENING = Pattern(f'({screen}|{famhx})')
