#! /usr/bin/env python
import os, json, csv, re
import shutil, textwrap
import argparse

JOINED_JSON = os.getenv("JOINED_JSON")

PARSED_JSON = os.getenv("PARSED_JSON")
CSV_DIR = os.getenv("CSV_DIR")
CATEGORY_LIST_JSON = os.getenv("CATEGORY_LIST_JSON")


YEAR_START = int(os.getenv("YEAR_START"))
YEAR_END = int(os.getenv("YEAR_END"))
NUM_YEARS = YEAR_END - YEAR_START + 1

def get_agencies(data):
    agencies = set()
    agency_years = dict()
    for year in data:
        agencies |= set(data[year].keys())
        for agency in data[year]:
            agency_years[agency] = agency_years.get(agency, set()) | {year}

    return agencies, agency_years

def agency_years_str(years):
    return ", ".join(sorted(years))

def invert_joined(joined):
    inverted = dict()
    for agency in joined:
        inverted[agency] = agency
        for alias in joined[agency]:
            inverted[alias] = agency
    return inverted

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

    with open(CATEGORY_LIST_JSON, 'r') as file:
        category_list = json.load(file)

    i_bottom = 99
    for category in CSVs.keys():
        print(category)

        i = None
        for index in range(len(category_list)):
            if category_list[index] == category:
                i = index
        if i is None:
            i = i_bottom
            i_bottom -= 1

        basename = f'{format_index(i)}-{category.replace("/", "_")}.csv'
        path = os.path.join(CSV_DIR, basename)
        with open(path, 'w') as file:
            writer = csv.writer(file)
            writer.writerows(CSVs[category])

def make_csvs(data, joined):
    CSVs = dict()

    if joined:
        joined = invert_joined(joined)
        replace_alias = lambda a: joined[a]
    else:
        replace_alias = lambda a: a

    for y in range(YEAR_START, YEAR_END + 1):
        year = str(y) + "-" + str(y + 1)[-2:]

        if year not in data: continue
        for agency in data[year]:
            canon_name = replace_alias(agency)
            for category in data[year][agency]:
                CSVs[category] = CSVs.get(category, make_years_list())
                if canon_name not in (c[0] for c in CSVs[category]):
                    CSVs[category].append( ['' for i in range(NUM_YEARS + 1)])
                    CSVs[category][-1][0] = canon_name

                for i in range(len(CSVs[category])):
                    if CSVs[category][i][0] == canon_name:
                        if CSVs[category][i][y - YEAR_START + 1]:
                            raise Exception('Cell already full. '
                                            f"{category=}, {year=}, {agency=}, "
                                            f"{canon_name=}, "
                                            f"{CSVs[category][i][y-YEAR_START + 1]=}, "
                                            f"{data[year][agency][category]=}")
                        CSVs[category][i][y - YEAR_START + 1] = data[year][agency][category]
                        break
    return CSVs

def combine(data):
    freq_dict = dict()
    agency_terms = dict()
    agencies, agency_years = get_agencies(data)

    for agency in agencies:
        split = agency.split(' ')
        split = [ re.sub(r'\W+', '', word).upper() for word in split ]
        split = [ word for word in split if word != '' ]
        for term in split:
            freq_dict[term] = freq_dict.get(term, set()) | {agency}
        agency_terms[agency] = split


    seen = set()
    if os.path.exists('joined.json'):
        with open('joined.json', 'r') as file:
            joined = json.load(file)
            for agency in joined:
                seen.add(agency)
                seen |= set(joined[agency])
    else:
        joined = dict()

    for agency in sorted(sorted(agency_terms.keys()), key=lambda t:len(agency_terms[t])):
        if agency in seen: continue
        alias_freq = dict()
        print(f'{agency} ({agency_years_str(agency_years[agency])})')
        for term in agency_terms[agency]:
            for alias in freq_dict[term]:
                if alias == agency: continue
                alias_freq[alias] = alias_freq.get(alias, 0) + 1
        sorted_aliases = sorted(alias_freq.keys(), key=lambda a: alias_freq[a],
                                reverse=True)
        sorted_aliases = [ s for s in sorted_aliases if s not in seen ]

        for i in range(len(sorted_aliases)):
            alias = sorted_aliases[i]
            if alias not in seen:
                main_text = f'   {i} - {alias} ('
                year_text = textwrap.wrap(agency_years_str(agency_years[alias]), 
                                          width=shutil.get_terminal_size()[0] - len(main_text) - 1,
                                          subsequent_indent=' ' * len(main_text))
                print(f"{main_text}{'\n'.join(year_text)})")

        while True:
            inp = input('>> ')
            if inp in sorted_aliases:
                alias = inp
            elif inp.isdigit() and 0 <= int(inp) < len(sorted_aliases):
                alias = sorted_aliases[int(inp)]
                if alias not in sorted_aliases:
                    print('Error.')
                    continue
            elif inp == 'next' or inp == 'N': 
                joined[agency] = joined.get(agency, []) + [agency]
                seen.add(agency)
                break
            elif inp == 'skip' or inp == 'S':
                break
            elif inp == 'exit': exit()
            else:
                print('Error.')

            joined[agency] = joined.get(agency, []) + [alias]
            seen.add(alias)
            print(f'{agency} - ({", ".join(joined[agency])})')
            years = agency_years_str({ year for a in joined[agency] for year in agency_years[a]}
                                     | agency_years[agency])
            print(f'Years: {years}')
            
            if len(joined[agency]) == len(sorted_aliases):
                joined[agency] = joined.get(agency, []) + [agency]
                seen.add(agency)
                break

        with open('joined.json', 'w') as file:
            json.dump(joined, file, indent=1)

    shuffled = dict()
    for agency in joined:
        most_recent = max(joined[agency], key=lambda a:max(agency_years[a]))
        shuffled[most_recent] = joined[agency]

    with open('joined.json', 'w') as file:
        json.dump(shuffled, file, indent=1)

    return shuffled

if __name__ == '__main__':
    parser = argparse.ArgumentParser() 
    parser.add_argument('-noi', '--no-interact', action='store_true')
    parser.add_argument('-nos', '--no-save', action='store_true')
    parser.add_argument('-C', '--combine', action='store_true')
    parsed_args = parser.parse_args()

    with open(PARSED_JSON, 'r') as file:
        data = json.load(file)

    joined = None
    if parsed_args.combine and not parsed_args.no_interact:
        joined = combine(data)

    if not parsed_args.no_save:
        CSVs = make_csvs(data, joined)
        write_to_csv(CSVs)

