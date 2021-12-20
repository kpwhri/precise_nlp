POLYP_IDENTIFIERS = {
    'diminutive': 1,
    'dim': 1,
    'small': 1,
    'medium': 5,
    'moderate': 5,
    'large': 10,
}

POLYP_IDENTIFIERS_PATTERN = f"(?:{'|'.join(POLYP_IDENTIFIERS.keys())})"
