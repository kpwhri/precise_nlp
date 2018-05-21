from enum import Enum


class AdenomaCountMethod(Enum):
    COUNT_IN_JAR = 1
    ONE_PER_JAR = 2


class Histology(Enum):
    TUBULAR = 1
    TUBULOVILLOUS = 2
    VILLOUS = 3
