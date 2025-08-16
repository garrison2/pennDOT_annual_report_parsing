#! /usr/bin/env python
import os, sys, json, re
import pdfplumber

import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

REPORTS_DIR = os.getenv("REPORTS_DIR")
FORMAT_JSON = os.getenv("FORMAT_JSON")
PARSED_JSON = os.getenv("PARSED_JSON")
TMP_JSON = os.getenv("TMP_JSON")
REPORT_NAME_FORMAT = os.getenv("REPORT_NAME_FORMAT")
YEAR_START = os.getenv("YEAR_START")
YEAR_END = os.getenv("YEAR_END")

BOXES = [ 'lbox', 'rbox', 'tbox', 'lchart', 'rchart' ]

# -------------- HELPER --------------
def clean(val):
    if isinstance(val, list):
        if len(val) != 1:
            val = [ clean(v) for v in val ]
            return val
        else:
            val = val[0]
    return int(val) if val.isdigit() else val
# ------------------------------------

def get_format_dict():
    with open(FORMAT_JSON, "r") as file:
        format_dict = json.load(file)

    if os.path.exists(TMP_JSON):
        open_tmp = input("Open tmp format file? (y/n) ")
        if open_tmp == 'y':
            with open(TMP_JSON, "r") as file:
                format_dict = json.load(file)
    return format_dict

def write_to_file(dict_dump, filepath):
    with open(filepath, 'w') as file:
        json.dump(dict_dump, file, indent=1)

def change_year_format(format_dict, year, prior):
    if prior not in format_dict: return format_dict[year]

    for category in format_dict[year]['categories']:
        cbase = format_dict[year]['categories'][category]
        pbase = format_dict[prior]['categories'][category]
        for item in cbase:
            if item == 'subheadings': continue
            if cbase[item] is None:
                cbase[item] = pbase.get(item)

        if 'subheadings' in cbase:
            sbase = cbase['subheadings']
            psbase = pbase.get('subheadings', dict())
            for item in sbase:
                if item is None:
                    sbase[item] = psbase.get(item)

    write_to_file(format_dict, TMP_JSON)

def get_agency_range(meta):
    pages_per_agency = int(meta["Pages Per Agency"])
#     exception = meta.get('PPA_exception')
#     if exception:
#         exception = exception.split(' ')
#         exception[0] = int(exception[0])
#         exception[1] = int(exception[1])
# 
# # TODO

    index0 = int(meta["Urban Systems (Start Page)"])
    index1 = int(meta["Rural Systems (Start Page)"])
    index2 = int(meta["Shared Ride (Start Page)"])

    urban = range(index0, index1 - 2, pages_per_agency)
    rural = range(index1, index2 - 2, pages_per_agency)

#    if exception and i == exception[0] + :
#        i -= int(meta["Pages Per Agency"])
#        i += exception[1]
#


    return list(urban) + list(rural)

def get_box_text(page, meta) -> dict:
    box_text = dict()
    for box in meta['boxes']:
        dimensions = meta['boxes'][box]
        box_text[box] = page.crop(dimensions).extract_text()
    return box_text

def get_lrbox_index(box_text, categories) -> dict:
    tmp_index = {'lbox':[], 'rbox':[]}
               
    for category in categories:
        box = categories[category]['box']
        if box != 'lbox' and box != 'rbox': continue

        search_text = box_text[box]
        pattern = categories[category]['name']
        if pattern is None:
            continue

        search = re.search(pattern, search_text, flags=re.DOTALL)
        if search:
            tmp_index[box].append((category, search.end()))
            continue

        print(f'Error: {repr(pattern)}')
        print(repr(search_text))

    tmp_index['lbox'].sort(key=lambda x:x[1])
    tmp_index['rbox'].sort(key=lambda x:x[1])

    index = {'lbox':dict(), 'rbox':dict()}
    for box in index:
        tmp_box = tmp_index[box]
        for i in range(len(tmp_box) - 1):
            name, start = tmp_box[i]
            end = tmp_box[i + 1][1]
            index[box][name] = (start, end)
        name, start = tmp_box[len(tmp_box) - 1]
        end = len(box_text[box])
        index[box][name] = (start, end)

    return index

def match_lrbox(cbase, text, start, end, silent = False):
    vals = dict()
    for subcat in cbase['subheadings']:

        scbase = cbase['subheadings'][subcat]
        if scbase['name'] == '': continue

        pattern1 = f"{scbase['name']}.*?\n"
        pattern2 = f"{scbase['name']}.*?$"
        search = (re.search(pattern1, text[start:end])
                  or re.search(pattern2, text[start:end]))
        if search:
            tmp = search.group(0)
            tmp = tmp[len(scbase['name']):]
            tmp = tmp.strip()
            tmp = tmp.split(scbase['delim'])
            tmp = [ r.strip() for r in tmp[1:] ] if len(tmp) > 1 else tmp
            vals[subcat] = clean(tmp)
        else:
            vals[subcat] = "_"
            if silent: continue
            print(f'\t{subcat} | {repr(scbase['name'])} | '
                  f'{repr(text[start:end])} | Not Found.')

    if cbase['delim'] is not None:
        search = re.search(cbase['name'], text[start:end])
        if search:
            tmp = search.split(scbase['delim'])
            vals[subcat] = clean(tmp)



    return vals

def main(start = None):
    format_dict = get_format_dict()
    if os.path.exists(PARSED_JSON):
        with open(PARSED_JSON, 'r') as file:
            results = json.load(file)
    else:
        results = dict()

    csvs = dict()

    start = start if start else int(YEAR_START)
    end = int(YEAR_END) + 1

    for y in range(start, end):
        year = str(y) + "-" + str(y + 1)[-2:]
        prior = str(y - 1) + "-" + str(y)[-2:]
        filepath = os.path.join(REPORTS_DIR, REPORT_NAME_FORMAT.format(year=year))

        change_year_format(format_dict, year, prior)

        meta = format_dict[year]['meta']
        categories = format_dict[year]['categories']

        results[year] = dict()

        with open(filepath, 'rb') as file:
            pdf = pdfplumber.open(file)

            print(f'Year: {year}')

            for i in get_agency_range(meta):
                if 'except' in meta and i in meta['except']:
                    continue
                page = pdf.pages[i - 1]

                box_text = get_box_text(page, meta)
                index = get_lrbox_index(box_text, categories)

                name = None
                vals = dict()
                for category in categories:
                    cbase = categories[category]
                    if cbase['name'] == '': continue

                    silent = False
                    if meta.get('silent') and category in meta['silent']:
                        silent = True

                    match cbase['box']:
                        case 'tbox':
                            name = box_text['tbox'].replace("\n", " ")
                            print(name)
                        case 'lchart' | 'rchart':
                            pass
                        case _:
                            try:
                                text = box_text[cbase['box']]
                                start, end = index[cbase['box']][category]
                            except KeyError as e:
                                print(f'box_text: {box_text}')
                                print(f'cbase: {cbase}')
                                print(f'page: {i}')
                                raise e

                            vals |= match_lrbox(cbase, text, start, end,
                                                silent = silent)

                results[year][name] = vals
                write_to_file(results, PARSED_JSON)


if __name__ == '__main__':
    start = None
    if len(sys.argv) == 3 and sys.argv[1] == 'year':
        start = int(sys.argv[2])
    main(start)
