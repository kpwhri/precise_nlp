"""
Variable overview:

If a total, then divided by <3, 3+
Otherwise, yes=1, no=0
"""
# adenoma detected
ADENOMA_STATUS = 'adenoma_status'
ADENOMA_STATUS_ADV = 'adenoma_status_adv'
ADENOMA_DISTAL = 'adenoma_distal'
ADENOMA_DISTAL_COUNT = 'adenoma_distal_count'
ADENOMA_PROXIMAL = 'adenoma_proximal'
ADENOMA_PROXIMAL_COUNT = 'adenoma_proximal_count'
ADENOMA_RECTAL = 'adenoma_rectal'
ADENOMA_RECTAL_COUNT = 'adenoma_rectal_count'
ADENOMA_UNKNOWN = 'adenoma_unknown'
ADENOMA_UNKNOWN_COUNT = 'adenoma_unknown_count'
JAR_ADENOMA_COUNT_ADV = 'jar_adenoma_count_adv'
JAR_ADENOMA_DISTAL_COUNT = 'jar_adenoma_distal_count'
JAR_ADENOMA_PROXIMAL_COUNT = 'jar_adenoma_proximal_count'
JAR_ADENOMA_RECTAL_COUNT = 'jar_adenoma_rectal_count'
JAR_ADENOMA_UNKNOWN_COUNT = 'jar_adenoma_unknown_count'

# tubulovillous adenoma detected
TUBULOVILLOUS = 'tubulovillous'
# tubular adenoma detected
TUBULAR = 'tubular'
# villous adenoma detected (not tubulovillous)
VILLOUS = 'villous'
# either villous or tubulovillous adenoma detected
ANY_VILLOUS = 'any_villous'
PROXIMAL_VILLOUS = 'proximal_villous'
DISTAL_VILLOUS = 'distal_villous'
RECTAL_VILLOUS = 'rectal_villous'
UNKNOWN_VILLOUS = 'unknown_villous'
# high-grade dysplasia detected
HIGHGRADE_DYSPLASIA = 'highgrade_dysplasia'
SIMPLE_HIGHGRADE_DYSPLASIA = 'simple_highgrade_dysplasia'
# number of adenomas found
ADENOMA_COUNT = 'adenoma_count'
ADENOMA_COUNT_ADV = 'adenoma_count_adv'
# has adenoma >= X size
LARGE_ADENOMA = 'large_adenoma'
# sessile serrated adenoma/polyp; SSA/SSP
JAR_SESSILE_SERRATED_ADENOMA_COUNT = 'jar_sessile_serrated_adenoma_cnt'
# number of carcinomas
CARCINOMA_COUNT = 'jar_carcinoma_count'
CARCINOMA_MAYBE_COUNT = 'jar_carcinoma_maybe_count'
CARCINOMA_POSSIBLE_COUNT = 'jar_carcinoma_possible_count'
CARCINOMA_IN_SITU_COUNT = 'jar_carcinoma_in_situ_count'
CARCINOMA_IN_SITU_POSSIBLE_COUNT = 'jar_carcinoma_in_situ_poss_cnt'
CARCINOMA_IN_SITU_MAYBE_COUNT = 'jar_carcinoma_in_situ_maybe_cnt'
