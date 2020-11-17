import re

from precise_nlp.extract.path.path_word import PathWord


class PathSection:
    WORD_SPLIT_PATTERN = re.compile(r'([a-z]+|[0-9]+(?:\.[0-9]+)?)')
    PREPROCESS = {re.escape(k) if esc else k: v for k, v, esc in (
        # 1 to use regex escape, 0 if you want to use a regex
        ('tubularadenoma', 'tubular adenoma', 1),
        ('tubularadenomas', 'tubular adenomas', 1),
        ('multipletubular', 'multiple tubular', 1),
        ('noevidence', 'no evidence', 1),
        ('polyppathologist', 'polyp pathologist', 1),
    )}
    PREPROCESS_RX = re.compile("|".join(PREPROCESS.keys()))

    def __init__(self, section):
        pword = None
        pindex = 0
        section = self._preprocess(section)
        self.section = []
        word_index = 0
        for m in self.WORD_SPLIT_PATTERN.finditer(self._preprocess(section)):
            if pword:  # get intervening punctuation
                self.section.append(PathWord(pword, word_index, section[pindex:m.start()]))
                word_index += 1
            pword = section[m.start(): m.end()]
            pindex = m.end()
        if pword:
            self.section.append(PathWord(pword, word_index, section[pindex:]))
        self.curr = None

    def _preprocess(self, text):
        return self.PREPROCESS_RX.sub(lambda m: self.PREPROCESS[re.escape(m.group(0))], text, re.IGNORECASE)

    def __iter__(self):
        for i, section in enumerate(self.section):
            self.curr = i
            yield section

    def __getitem__(self, item):
        return self.section[item]

    def iter_prev_words(self):
        for word in reversed(self.section[0: self.curr]):
            yield word

    def has_before(self, terms, *, window=5, offset=0, allow_stop=True):
        """
        Example sentence: w0 w1 w2 w3 w4 w5
        * If offset=2 and window=5, and current word is w5, we'll look at (w0, w1, and w2)

        :param terms:
        :param window: how far back to look
        :param offset: skip this many
        :param allow_stop:
        :return:
        """
        for word in reversed(self.section[max(self.curr - window, 0): self.curr - offset]):
            if allow_stop and word.stop():
                return False
            if word.isin(terms):
                return word
        return False

    def has_after(self, terms, *, window=5, offset=0, allow_stop=True):
        for word in self.section[self.curr + 1 + offset:min(self.curr + window + 1, len(self.section))]:
            if word.isin(terms):
                return word
            if allow_stop and word.stop():  # punctuation after word
                return False
        return False
