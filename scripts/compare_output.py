import csv
import json
import sys
from collections import defaultdict
from datetime import datetime


def parse_files(*files):
    file_alias = {}
    data = defaultdict(dict)
    for alias, file in enumerate(files):
        file_alias[file] = alias
        with open(file) as fh:
            for row in csv.DictReader(fh):
                identifier = row['identifier']
                del row['row']
                del row['identifier']
                data[alias][identifier] = row
    return data, file_alias


def main():
    if len(sys.argv) < 3:
        raise ValueError('Usage: compare_output.py output.csv output2.csv')
    data, file_alias = parse_files(*sys.argv[1:])
    report = defaultdict(dict)
    for identifier in data[0]:
        base, *others = tuple(data[alias][identifier] for alias in file_alias.values())
        for var, base_val in base.items():
            other_vals = (base_val,) + tuple(other[var] for other in others)
            if len(set(other_vals)) == 1:
                report[var]['agree'] = report[var].get('agree', 0) + 1
            else:
                report[var]['disagree'] = report[var].get('disagree', 0) + 1
                report[var]['disagreements'] = report[var].get('disagreements', list()) + [{
                    **{str(i): val for i, val in enumerate(other_vals)},
                    **{'identifier': identifier}
                }]
    with open(f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as out:
        out.write(json.dumps(
            {'alias': file_alias, 'report': report}, sort_keys=True, indent=4)
        )


if __name__ == '__main__':
    main()
