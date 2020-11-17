import re


class PathWord:
    STOP = re.compile(r'.*([:.]).*')

    def __init__(self, word, index, spl=''):
        self.word = word
        self.spl = spl  # not part of object itself
        self.index = index

    def isin(self, lst):
        return self.word in lst

    def matches(self, pattern):
        return pattern.match(self.word)

    def match(self, pattern):
        return pattern.match(self.word).group(1)

    def stop(self):
        return PathWord.STOP.match(self.spl)

    def __eq__(self, other):
        """Does not rely on punctuation"""
        if isinstance(other, PathWord):
            return self.word == other.word
        return self.word == other

    def __contains__(self, other):
        return other in self.word

    def __str__(self):
        return self.word

    def __bool__(self):
        return True

    def __hash__(self):
        """Does not rely on punctuation"""
        return hash(self.word)
