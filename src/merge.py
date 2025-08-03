#! /usr/bin/env python
import csv, json, os

FORMAT_JSON = os.getenv("FORMAT_JSON")
MERGE_JSON = os.getenv("MERGE_JSON")
TMP_JSON = os.getenv("TMP_JSON")

def merge():
    with open(FORMAT_JSON, 'r') as file:
        format_dict = json.load(file)

    with open(MERGE_JSON) as file:
        merge_dict = json.load(file)

    for year in format_dict:
        if year not in merge_dict:
            continue

        format_year = format_dict[year]
        merge_year = merge_dict[year]
        shared = set(format_year.keys()) | set(merge_year.keys())
        for item in shared:
            if item in format_year and item in merge_year:
                format_dict[year][item] = merge_year[item] | format_year[item]
            elif item in merge_year:
                format_dict[year][item] = merge_dict[item]

    if os.path.exists(TMP_JSON):
        print(f'{TMP_JSON} already exists.')
        return
    with open(TMP_JSON, 'w') as f:
        json.dump(format_dict, f, indent=1)

if __name__ == '__main__':
    merge()

