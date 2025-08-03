#! /usr/bin/env python
import json, re, os, io, subprocess, shutil, sys
import pdfplumber

import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

REPORTS_DIR = os.getenv("REPORTS_DIR")
FORMAT_JSON = os.getenv("FORMAT_JSON")
REPORT_NAME_FORMAT = os.getenv("REPORT_NAME_FORMAT")
YEAR_START = os.getenv("YEAR_START")
YEAR_END = os.getenv("YEAR_END")

BOXES = [ 'lbox', 'rbox', 'tbox', 'lchart', 'rchart' ]

def get_agency_range(meta):
    startnum = int(meta["Urban Systems (Start Page)"])
    endnum = int(meta["Rural Systems (Start Page)"])
    pages_per_agency = int(meta["Pages Per Agency"])

    exception = meta.get('PPA_exception')
    if exception:
        exception = exception.split(' ')
        exception[0] = int(exception[0])
        exception[1] = int(exception[1])

    return (startnum, endnum, pages_per_agency, exception)

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
        search = re.search(pattern, search_text)
        if search:
            tmp_index[box].append((category, search.start()))
        else:
            print(f'Error {pattern}!')
            print(search_text)

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

def main():
    with open(FORMAT_JSON, 'r') as file:
        format_dict = json.load(file)

    csvs = dict()

    for y in range(int(YEAR_START), int(YEAR_END) + 1):
        year = str(y) + "-" + str(y + 1)[-2:]
        filepath = os.path.join(REPORTS_DIR, REPORT_NAME_FORMAT.format(year=year))

        meta = format_dict[year]['meta']
        categories = format_dict[year]['categories']

        with open(filepath, 'rb') as file:
            pdf = pdfplumber.open(file)

            print(f'Year: {year}')

            pagestart, pageend, per_agency, exception = get_agency_range(meta)
            for i in range(pagestart, pageend, per_agency):
                print('\nnew page')
                page = pdf.pages[i - 1]

                box_text = get_box_text(page, meta)
                index = get_lrbox_index(box_text, categories)
                print(index)

                for category in categories:
                    cbase = categories[category]
                    if cbase['name'] == '': continue

                    match cbase['box']:
                        case 'tbox':
                            pass
                        case 'lchart' | 'rchart':
                            pass
                        case _:
                            text = box_text[cbase['box']]
                            start, end = index[cbase['box']][category]

                            for subcat in cbase['subheadings']:
                                scbase = cbase['subheadings'][subcat]
                                if scbase['name'] == '': continue

                                pattern1 = f"{scbase['name']}.*?\n"
                                pattern2 = f"{scbase['name']}.*?$"
                                search = (re.search(pattern1, text[start:end])
                                          or re.search(pattern2, text[start:end]))
                                if search:
                                    result = search.group(0)
                                    result = result[len(scbase['name']):]
                                    result = result.strip()
                                    result = result.split(scbase['delim'])
                                    result = [ r.strip() for r in result[1:] ]
                                    print(subcat, result)
                                else:
                                    print(repr(pattern))
                                    print(repr(text[start:end]))
                                    print('Not Found.')

                            if cbase['delim'] is not None:
                                search = re.search(cbase['name'], text[start:end])
                                if search:
                                    print(search.split(scbase['delim']))

                if exception and i == exception[0]:
                    i -= per_agency
                    i += exception[1]

if __name__ == '__main__':
    main()
