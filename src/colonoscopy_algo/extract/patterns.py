import re

NUMBER_PATTERN = re.compile(r'(\d{1,3})', re.IGNORECASE)
DEPTH_PATTERN = re.compile(r'(\d{1,3})\W*[cm]m', re.IGNORECASE)
SIZE_PATTERN = re.compile(r'(?<!at|\W@)\W*(<\d{1,3}(?:\.\d)?)\W*[cm]m', re.IGNORECASE)
AT_DEPTH_PATTERN = re.compile(r'(?:at|@)\W*(\d{1,3}(?:\.\d)?)\W*[cm]m', re.IGNORECASE)
CM_DEPTH_PATTERN = re.compile(r'(\d{2,3})\W*cm', re.IGNORECASE)
