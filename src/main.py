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

def main():
    with open(FORMAT_JSON, 'r') as file:
        format_dict = json.load(file)

    csvs = dict()

    for y in range(int(YEAR_START), int(YEAR_END) + 1):
        year = str(y) + "-" + str(y + 1)[-2:]
        filepath = os.path.join(REPORTS_DIR, REPORT_NAME_FORMAT.format(year=year))

        with open(filepath, 'rb') as file:
            pdf = pdfplumber.open(file)

            print(f'Year: {year}')

            startnum = int(format_dict[year]['meta']["Urban Systems (Start Page)"])
            endnum = int(format_dict[year]['meta']["Rural Systems (Start Page)"])
            pages_per_agency = int(format_dict[year]['meta']["Pages Per Agency"])

            for i in range(startnum, endnum, pages_per_agency):
                page = pdf.pages[i - 1]

                for category in format_dict[year]['categories']:
                    name, x0, x1, y0, y1 = format_dict[year]['categories'][category]
                    if name == '': continue

                    direction = 'top'
                    while True:
                        try:
                            cropped = page.crop((x0, y0, x1, y1))
                        except ValueError as e:
                            print("\nError! Bounding box larger than page dimensions.\n")
                        else:
                            text = "".join([c['text'] for c in cropped.chars])

                        if name and name not in text:
                            if direction == 'top':
                                if y0 - 50 < 0:
                                    direction = 'bottom'
                                    continue
                                y0 -= 50 
                                y1 -= 50

                            else:
                                if (y1 + 50 > page.height):
                                    print("Could not find")
                                    break

                                y0 += 50
                                y1 += 50
                        else:
                            break



                    if name == None: name = ''
                    if category == "Act 44 Fixed Route Distribution Factors":
                        category = "Act 44 Factors"


                    terminal_width = shutil.get_terminal_size().columns
                    yr_wdth = int(terminal_width * 0.1)
                    cat_wdth = int(terminal_width * 0.2)
                    name_wdth = int(terminal_width * 0.2)
                    text_wdth = int(terminal_width * 0.5)


                    print(f'{year}{" " * (yr_wdth - len(year))}'
                          f'{category}{" " * (cat_wdth - len(category))}'
                          f'{name}{" " * (name_wdth - len(name))}'
                          f'{text}{" " * (text_wdth - len(text))}'
                          )


if __name__ == '__main__':
    main()
