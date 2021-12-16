POLYP_IDENTIFIERS = {
    'diminutive': 1,
    'small': 1,
    'medium': 5,
    'medium sized': 5,
    'moderate': 5,
    'moderately sized': 5,
    'large': 10,
}

POLYP_IDENTIFIERS_PATTERN = f"(?:{'|'.join(POLYP_IDENTIFIERS.keys())})"
