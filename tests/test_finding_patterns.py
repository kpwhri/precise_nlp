import pytest

from precise_nlp.extract.cspy.finding_patterns import apply_finding_patterns, apply_finding_patterns_to_location, \
    remove_finding_patterns, regex_strip


@pytest.mark.parametrize('text, exp_count, exp_size, exp_locations', [
    ('Polyp (15 mm) in the descending colon', 1, 15, {'descending'}),
    ('Polyp (10 mm)-in the sigmoid colon. (Polypectomy)', 1, 10, {'sigmoid'}),
    ('Polyp (10 mm)-in the distal sigmoid colon. (Polypectomy)', 1, 10, {'sigmoid'}),
    ('Polyp (12 mm) in the splenic flexure. (Polypectomy)', 1, 12, {'splenic'}),
    ('Polyps (2 mm to 4 mm) In the ascending colon (polyps)', 2, 4, {'ascending'}),
    ('Polyps (2 mm to 4 mm) In the rectum (polyps)', 2, 4, {'rectum'}),
    ('Polyps (2 mm to 4 mm) In the ascending colon (polyps) and rectum (polyps)', 2, 4, {'ascending', 'rectum'}),
    ('One 3 mm polyp in the descending colon', 1, 3, {'descending'}),
    ('One diminutive polyp in the cecum', 1, 1, {'cecum'}),
    ('Two medium sized polyps in the cecum', 2, 5, {'cecum'}),
    ('Three moderately-sized polyps in the cecum', 3, 5, {'cecum'}),
    ('Ten large polyps in the cecum', 10, 10, {'cecum'}),
    ('One small polyp in the descending colon', 1, 1, {'descending'}),
    ('Four 3 to 5 mm polyps in the rectum', 4, 5, {'rectum'}),
    ('POLYP: Location: Descending colon. Size: 5 mm', 1, 5, {'descending'}),
    ('Transverse Colon - one 5 mm sessile polyp(s) (removed with jumbo biopsy forceps)', 1, 5, {'transverse'}),
    ('Sigmoid Colon - one 10 mm sessile polyp(s)', 1, 10, {'sigmoid'}),
    ('Rectum - two 2 mm sessile polyp(s)', 2, 2, {'rectum'}),
    ('Sigmoid Colon - two 15 mm pedunculated polyp(s)', 2, 15, {'sigmoid'}),
    ('Cecum - one 5 mm flat polyp(s)', 1, 5, {'cecum'}),
    ('Cecum - Large 1 cm polyp removed at the ileocecal valve with cautery snare', 1, 10, {'cecum'}),
    ('Sigmoid Colon - one diminutive   sessile polyp', 1, 1, {'sigmoid'}),
    ('Cecum - two dim polyp(s) ', 2, 1, {'cecum'}),
    ('Sigmoid Colon - two 3-4 mm sessile polyp(s)', 2, 4, {'sigmoid'}),
    ('Anorectum - three 3-4 mm sessile polyp', 3, 4, {'anus', 'rectum'}),
    ('Descending:  4 sessile polyps.  The polyps were 6 mm in diameter', 4, 6, {'descending'}),
    ('Sigmoid:   Diverticulosis.  1 pedunculated polyp.  The polyp was 2.0 cm in diameter', 1, 20, {'sigmoid'}),
    ('Cecum - two 3 mm and 13 mm sessile polyp(s)', 2, 13, {'cecum'}),
    ('Ascending Colon - three 3-5 mm sessile polyp(s)', 3, 5, {'ascending'}),
    ('Polyp (12 mm) tn the splenic flexure', 1, 12, {'splenic'}),
    ('Polyp (15 mm) In the Colon @ 30cm.', 1, 15, {'sigmoid'}),
])
def test_finding_pattern(text, exp_count, exp_size, exp_locations):
    findings = list(apply_finding_patterns(text))
    print(findings)
    assert len(findings) == 1, 'No findings found in text'
    assert findings[0].count == exp_count
    assert findings[0].size == exp_size
    assert set(findings[0].locations) == set(exp_locations)


@pytest.mark.parametrize('text, exp_count, exp_size', [
    ('one 5 mm sessile polyp(s) (removed with jumbo biopsy forceps)', 1, 5),
    ('one 10 mm sessile polyp(s)', 1, 10),
    ('two 2 mm sessile polyp(s)', 2, 2),
    ('two 15 mm pedunculated polyp(s)', 2, 15),
    ('one 5 mm flat polyp(s)', 1, 5),
    ('Large 1 cm polyp removed at the ileocecal valve with cautery snare', 1, 10),
    ('one diminutive   sessile polyp', 1, 1),
    ('two dim polyp(s) ', 2, 1),
    ('two 3-4 mm sessile polyp(s)', 2, 4),
    ('three 3-4 mm sessile polyp', 3, 4),
    ('4 sessile polyps.  The polyps were 6 mm in diameter', 4, 6),
    ('Diverticulosis.  1 pedunculated polyp.  The polyp was 2.0 cm in diameter', 1, 20),
    ('two 3 mm and 13 mm sessile polyp(s)', 2, 13),
    ('three 3-5 mm sessile polyp(s)', 3, 5),
])
def test_finding_pattern_in_location(text, exp_count, exp_size):
    location = 'sigmoid'  # just default to anything
    findings = list(apply_finding_patterns_to_location(text, location))
    print(findings)
    assert len(findings) == 1, 'No findings found in text'
    assert findings[0].count == exp_count
    assert findings[0].size == exp_size


@pytest.mark.parametrize('text, exp_findings_count, exp_count, exp_max_size', [
    ('one 2-3 mm sessile polyp(s) (removed with biopsy forceps), one 6-7 mm sessile polyp', 2, 2, 7),
])
def test_finding_pattern_in_location_on_multiple(text, exp_findings_count, exp_count, exp_max_size):
    location = 'sigmoid'  # just default to anything
    findings = list(apply_finding_patterns_to_location(text, location))
    print(findings)
    assert len(findings) == exp_findings_count, 'No findings found in text'
    assert sum(finding.count for finding in findings) == exp_count
    assert max(finding.size for finding in findings) == exp_max_size


@pytest.mark.parametrize('text, exp, exp_normal', [
    (
            '''Terminal ileum: not evaluated  · Cecum:   Normal   · Ascending: 1 sessile polyp.  The polyp was 6 mm in 
            diameter and removed using removed with jumbo biopsy forceps.  · Transverse:  Normal  · Descending:  Normal
              · Sigmoid:   Normal  · Rectum:  normal  · Anorectum: normal''',
            {'ileum', 'cecum', 'ascending', 'sigmoid', 'rectum', 'anus', 'rectum', 'descending', 'transverse'},
            {'cecum', 'transverse', 'descending', 'sigmoid', 'rectum', 'anus', 'rectum'}
    ),
])
def test_split_by_location(cspy, text, exp, exp_normal):
    locations_dict = cspy.split_by_location(text)
    locations = {el for key in locations_dict.keys() for el in key}
    assert locations == exp
    normal_locations = {el for key, value in locations_dict.items() for el in key if 'normal' in value.lower()}
    assert normal_locations == exp_normal


@pytest.mark.parametrize('text, exp', [
    ('Polyp (15 mm) in the descending colon', ''),
    ('Polyp (10 mm)-in the sigmoid colon. (Polypectomy)', '. (Polypectomy)'),
    ('Polyp (10 mm)-in the distal sigmoid colon. (Polypectomy)', '. (Polypectomy)'),
    ('Polyp (12 mm) in the splenic flexure. (Polypectomy)', '. (Polypectomy)'),
    ('Polyps (2 mm to 4 mm) In the ascending colon (polyps)', '(polyps)'),
    ('Polyps (2 mm to 4 mm) In the rectum (polyps)', '(polyps)'),
    ('Polyps (2 mm to 4 mm) In the ascending colon (polyps) and rectum (polyps)', '(polyps)'),
    ('One 3 mm polyp in the descending colon', ''),
    ('One diminutive polyp in the cecum', ''),
    ('Two medium sized polyps in the cecum', ''),
    ('Three moderately-sized polyps in the cecum', ''),
    ('Ten large polyps in the cecum', ''),
    ('One small polyp in the descending colon', ''),
    ('Four 3 to 5 mm polyps in the rectum', ''),
    ('POLYP: Location: Descending colon. Size: 5 mm', ''),
    ('Transverse Colon - one 5 mm sessile polyp(s) (removed with jumbo biopsy forceps)',
     '(s) (removed with jumbo biopsy forceps)'),
    ('Sigmoid Colon - one 10 mm sessile polyp(s)', '(s)'),
    ('Rectum - two 2 mm sessile polyp(s)', '(s)'),
    ('Sigmoid Colon - two 15 mm pedunculated polyp(s)', '(s)'),
    ('Cecum - one 5 mm flat polyp(s)', '(s)'),
    ('Cecum - Large 1 cm polyp removed at the ileocecal valve with cautery snare',
     'removed at the ileocecal valve with cautery snare'),
    ('Sigmoid Colon - one diminutive   sessile polyp', ''),
    ('Cecum - two dim polyp(s) ', '(s)'),
    ('Sigmoid Colon - two 3-4 mm sessile polyp(s)', '(s)'),
    ('Anorectum - three 3-4 mm sessile polyp', ''),
    ('Descending:  4 sessile polyps.  The polyps were 6 mm in diameter', 'in diameter'),
    ('Sigmoid:   Diverticulosis.  1 pedunculated polyp.  The polyp was 2.0 cm in diameter', 'in diameter'),
    ('Cecum - two 3 mm and 13 mm sessile polyp(s)', '(s)'),
    ('Ascending Colon - three 3-5 mm sessile polyp(s)', '(s)'),
])
def test_remove_finding_patterns(text, exp):
    new_text = remove_finding_patterns(text)
    assert new_text == exp


@pytest.mark.parametrize('text, exp', [
    ('.te.rm', 'te.rm'),
    ('..te.rm', 'te.rm'),
    ('te.rm.', 'te.rm'),
    ('te.rm..', 'te.rm'),
    (' .te.rm.', 'te.rm'),
])
def test_regex_strip(text, exp):
    assert regex_strip(text) == exp
