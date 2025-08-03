#! /usr/bin/env python
import csv, json, os

FORMAT_CSV = os.getenv("FORMAT_CSV")
FORMAT_JSON = os.getenv("FORMAT_JSON")

META_END = int(os.getenv("META_END"))
CATEGORY_ITEMS = [clean(a) for a in os.getenv("CATEGORY_ITEMS").split(','))

def clean(arg):
    if arg.isdigit(): return int(arg)
    if arg == 'FALSE': return False
    if arg == 'TRUE': return True
    if arg == 'None': return None
    return arg

def main():
    years = dict()

    with open(FORMAT_CSV, 'r') as csv_file:
        reader = csv.reader(csv_file, delimiter=',')

        header = next(reader)
        for row in reader:
            year = row[0]
            years[year] = dict()
            years[year]['meta'] = dict()
            years[year]['categories'] = dict()
            for i in range(1, META_END):
                years[year]['meta'][header[i]] = clean(row[i])
            for i in range(META_END, len(header)):
                years[year]['categories'][header[i]] = [ clean(row[i]), 
                                                        *CATEGORY_ITEMS ]

    with open(FORMAT_JSON, 'w') as json_file:
        json.dump(years, json_file, indent=1)

#     for year in years:
#        print(year, years[year])

if __name__ == '__main__':
    main()
