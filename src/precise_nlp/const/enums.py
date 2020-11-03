from enum import Enum


class AdenomaCountMethod(Enum):
    COUNT_IN_JAR = 1
    ONE_PER_JAR = 2


class Histology(Enum):
    TUBULAR = 1
    TUBULOVILLOUS = 2
    VILLOUS = 3


class Location(Enum):
    ANY = 1
    PROXIMAL = 2
    DISTAL = 3
    RECTAL = 4
    UNKNOWN = 5


class AssertionStatus(Enum):
    UNKNOWN = -1
    NEGATED = 0
    IMPROBABLE = 1
    POSSIBLE = 2
    PROBABLE = 3
    DEFINITE = 4
