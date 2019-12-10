import re
import string


def remove_ocr_junk(line, remove_colon=True):
    if remove_colon:
        line = re.sub('The Colon', '', line)
    tokens = line.split()
    up_letters = re.compile(f'[{string.ascii_uppercase}]')
    lw_letters = re.compile(f'[{string.ascii_lowercase}]')
    exp_punct = re.compile(r'[.,]')
    numbers = re.compile(r'[0-9]')
    # number of letters/numbers with unexpected punctuation
    # length
    # language model n-grams
    scores = []  # higher score -> junk
    for token in reversed(tokens):
        ltoken = token.lower()
        size = len(token)
        up_let = len(up_letters.findall(token))
        lw_let = len(lw_letters.findall(token))
        punct = 1 if token[-1] in '.,' else 0
        nums = len(numbers.findall(token))
        rest = size - up_let - lw_let - nums - punct
        if size > 4:
            if size - lw_let - up_let - punct == 0 and up_let <= 1:
                break
            elif nums >= size - 1:
                break
            elif size > 5 and lw_let + up_let + punct >= size - 1:
                break
            elif size > 6 and lw_let + up_let + punct >= size - 2:
                break
            else:
                # TODO: check if is word
                # TODO: check if removing last letters creates a word
                scores.append(10)
        elif size == 1:
            if nums == 1:
                scores.append(0)
            elif token == 'a':
                scores.append(0)
            elif token == 'A':
                scores.append(2)
            else:
                scores.append(10)
        elif size == 2:
            if nums == 2:
                scores.append(0)
            elif nums == 1 and (up_let + lw_let == 1 or punct):
                scores.append(2)
            elif ltoken in ['in', 'an', 'on', 'or', 'no', 'it', 'to', 'by', 'of']:
                scores.append(1)
            else:
                scores.append(10)
        elif size == 3:
            if nums == 3:
                scores.append(0)
            elif ltoken in ['its', 'the', 'and', 'was']:
                scores.append(0)
            else:
                scores.append(10)
        elif size == 4:
            if nums in [3, 4]:
                scores.append(3)
            elif lw_let + punct + up_let == size and up_let <= 1:
                scores.append(0)
            elif lw_let == 0:
                scores.append(7)
            elif lw_let == size - 1:
                scores.append(3)
            else:
                scores.append(10)
    line_end = None
    for i, score in enumerate(scores):
        if score >= 5:
            line_end = i
    if line_end is None:
        return line
    else:
        return ' '.join(tokens[:-(line_end + 1)])


def parse_file(text):
    skip_pat = re.compile(
        r'('
        r'(gender|sex|(procedure:\W*)?date(\W*of\W*birth)?'
        r'|mrn|\w+\W*md|medicines?|age|(patient\W*)name'
        r'|images?|providers'
        r')\W*?:'
        r'|\d{1,3}[-/)]\W*\d{1,3}\W*[/-]\W*\d{2,4}'  # phone number/date
        r')', re.IGNORECASE
    )
    word_pat = re.compile(r'[^a-z]', re.I)
    header_pat = re.compile(r'[A-Z][A-Za-z]+:')
    md_pat = re.compile(r'\bM\W*D\b')
    page_pat = re.compile(r'page\W*\d', re.IGNORECASE)
    no_page_pat = re.compile(r'\W+\d{1,2}\W*')
    keywords = {'cecum', 'polyp', 'size', 'found', 'adenoma',
                'colon'}
    lines = []
    found_start = False
    skip_mode = True
    has_page = bool(page_pat.search(text))
    for line in text.split('\n'):
        line = remove_ocr_junk(line)
        # find procedure/findings
        if not line:
            continue
        elif md_pat.search(line):
            continue  # skip lines containing ref to doc
        elif skip_pat.search(line):
            skip_mode = True
        elif ((has_page and page_pat.search(line))
              or (not has_page and no_page_pat.match(line))):
            # page number
            found_start = False
            skip_mode = False
        elif header_pat.match(line):
            skip_mode = False
            found_start = True
            lines.append(line)
        elif not found_start and lines:
            # looking for start on subsequent page
            words = [x.lower() for x in word_pat.split(line)]
            if (len(words) > 10
                    or set(words) & keywords):  # at least 10 words suggests a sentence
                found_start = True
                skip_mode = False
                lines[-1] += ' ' + line
        elif skip_mode:
            continue
        else:
            if lines:
                lines[-1] += ' ' + line
            else:
                lines.append(line)
    return '\n'.join(lines)
