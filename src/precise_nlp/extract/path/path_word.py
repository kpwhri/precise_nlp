import re


class PathWord:
    STOP = re.compile(r'.*([:.]).*')

    def __init__(self, word, index, spl=''):
        self.word = word
        self.spl = spl  # not part of object itself
        self.index = index

    @property
    def word_lc(self):
        return self.word.lower()

    def lower(self):
        return self.word_lc

    def isin(self, lst):
        return self.word_lc in lst
    
    def endswith(self, *s: str):
        return self.word.endswith(s)

    def matches(self, pattern):
        return pattern.match(self.word)

    def match(self, pattern):
        return pattern.match(self.word).group(1)

    def stop(self):
        return PathWord.STOP.match(self.spl)

    def __eq__(self, other):
        """Does not rely on punctuation"""
        if isinstance(other, PathWord):
            return self.word_lc == other.word_lc
        return self.word_lc == other.lower()

    def __contains__(self, other):
        return other.lower() in self.word_lc

    def __str__(self):
        return self.word

    def __bool__(self):
        return True

    def __hash__(self):
        """Does not rely on punctuation"""
        return hash(self.word)
