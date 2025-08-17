#! /usr/bin/env python
import os, json, csv

PARSED_JSON = os.getenv("PARSED_JSON")
CSV_DIR = os.getenv("CSV_DIR")

YEAR_START = int(os.getenv("YEAR_START"))
YEAR_END = int(os.getenv("YEAR_END"))
NUM_YEARS = YEAR_END - YEAR_START + 1

def make_years_list():
    l = ['']
    for i in range(YEAR_START, YEAR_END + 1):
        l += [str(i)]
    return([l])

def print_csv(CSVs):
    for category in CSVs:
        print(category)
        for row in CSVs[category]:
            print(row)
        print()

def write_to_csv(CSVs):
    format_index = lambda i: str(i) if i >= 10 else f'0{i}'


    cat_names = list(CSVs.keys())
    for i in range(len(cat_names)):
        category = cat_names[i]
        print(category)
        basename = f'{format_index(i)}-{category.replace("/", "_")}.csv'
        path = os.path.join(CSV_DIR, basename)
        with open(path, 'w') as file:
            writer = csv.writer(file)
            writer.writerows(CSVs[category])

def main():
    with open(PARSED_JSON, 'r') as file:
        parsed = json.load(file)

    CSVs = dict()
    for y in range(YEAR_START, YEAR_END):
        year = str(y) + "-" + str(y + 1)[-2:]

        if year not in parsed: continue
        for agency in parsed[year]:
            for category in parsed[year][agency]:
                CSVs[category] = CSVs.get(category, make_years_list())
                if agency not in (c[0] for c in CSVs[category]):
                    CSVs[category].append( ['' for i in range(NUM_YEARS + 1)])
                    CSVs[category][-1][0] = agency

                for i in range(len(CSVs[category])):
                    if CSVs[category][i][0] == agency:
                        CSVs[category][i][y - YEAR_START + 1] = parsed[year][agency][category]
                        break
    return CSVs


if __name__ == '__main__':
    CSVs = main()
    write_to_csv(CSVs)

