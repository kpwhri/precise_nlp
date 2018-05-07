import re

NUMBER_PATTERN = re.compile(r'(\d{1,3})', re.IGNORECASE)
DEPTH_PATTERN = re.compile(r'(\d{1,3})\W*[cm]m', re.IGNORECASE)
# this should probably take the larger of the two options
# instead of ignoring the second
SIZE_PATTERN = re.compile(r'(<?\d{1,3}(?:\.\d)?)(?:\W*x\W*(?:\d{1,3}(?:\.\d)?))?\W*[cm]m', re.IGNORECASE)
AT_DEPTH_PATTERN = re.compile(r'(?:at|@|to)\W*(\d{1,3}(?:\.\d)?)\W*[cm]m', re.IGNORECASE)
CM_DEPTH_PATTERN = re.compile(r'(\d{2,3})\W*cm', re.IGNORECASE)
