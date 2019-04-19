import re


def parse_file(text):
    skip_pat = re.compile(
        r'(gender|sex|(procedure:\W*)?date(\W*of\W*birth)?'
        r'|mrn|\w+\W*md|medicines?|age|(patient\W*)name'
        r'|images?|providers'
        r'|\d{1,3}[-/)]\W*\d{1,3}\W*[/-]\W*\d{2,4}'  # phone number
        r')\W*?:', re.IGNORECASE
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
            lines[-1] += ' ' + line
    return '\n'.join(lines)
