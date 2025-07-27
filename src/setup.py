#! /usr/bin/env python
import json, re, os, io, subprocess, shutil, sys
import pdfplumber

REPORTS_DIR = os.getenv("REPORTS_DIR")
FORMAT_JSON = os.getenv("FORMAT_JSON")
REPORT_NAME_FORMAT = os.getenv("REPORT_NAME_FORMAT")
YEAR_START = os.getenv("YEAR_START")
YEAR_END = os.getenv("YEAR_END")

class YearFrame:
    def __init__(self, year, prior, pdf, filepath, format_dict):
        self.pdf = pdf
        self.year = year
        self.filepath = filepath
        self.meta = format_dict[year]['meta']
        self.categories = format_dict[year]['categories']

        if prior in format_dict:
            self.prior = format_dict[prior]['categories']
        else: self.prior = False

    def full(self):
        for category in self.categories:
            if not all(self.categories[category]): return False
        return True

    def get_prior(self, category):
        if self.prior:
            return tuple(self.prior[category][1:])
        else:
            return None

class LoopFrame:
    def __init__(self, category, page, pagenum, dimensions):
        self.category = category
        self.page = page
        self.pagenum = pagenum
        self.dimensions = dimensions
        self.run = True
        self.instruct = True
        self.end = False

def get_format_dict():
    with open(FORMAT_JSON, "r") as file:
        format_dict = json.load(file)

    if os.path.exists("tmp.json"):
        open_tmp = input("Open tmp format file? (y/n) ")
        if open_tmp == 'y':
            with open("tmp.json", "r") as file:
                format_dict = json.load(file)
    return format_dict

def loop_categories(yearframe, format_dict, skip=True):
    pagenum = yearframe.meta["Urban Systems (Start Page)"]
    page = yearframe.pdf.pages[pagenum - 1]


    for category in yearframe.categories:
        if skip and all(yearframe.categories[category][1:]): continue
        if yearframe.categories[category][0] == '': continue

        if all(yearframe.categories[category][1:]):
            dimensions = yearframe.categories[category][1:]
        else:
            dimensions = yearframe.get_prior(category)

        year_category = yearframe.categories[category][0]
        loopframe = LoopFrame(year_category, page, pagenum, dimensions)

        new_dimensions = loop(yearframe, loopframe)
        for i in range(0, 4):
            yearframe.categories[category][i+1] = new_dimensions[i]
        write_to_tmp(format_dict)

def loop(yearframe, loopframe): 
    while True:
        page = loopframe.page
        if loopframe.dimensions is None or not all(loopframe.dimensions):
            loopframe.dimensions = (0, page.width, 0, page.height)
        x0, x1, y0, y1 = loopframe.dimensions

        if loopframe.run:
            print(f"Dimensions: ({x0}, {x1}, {y0}, {y1})")
            print(f"Width: {page.width}, Height: {page.height}")
            print(f"Category: {loopframe.category}")

            try:
                cropped = page.crop((x0, y0, x1, y1))
            except ValueError as e:
                print("\nError! Bounding box larger than page dimensions.\n")
            else:
                print()
                for char in cropped.chars:
                    print(char['text'], end='')
                print()

        if loopframe.instruct:
            print("\nUse:\n"
                  "\th to show this help\n"
                  "\to to open file\n"
                  "\tV to view changes\n"
                  "\tN to save and go to the next category\n\n"
                  "\t[id]+ [num] to increase a dimension\n"
                  "\t[id]- [num] to decrease a dimension\n"
                  "\t[id] [num] to set a dimension\n"
                  "\t\twhere id = x0, x1, y0, or y1\n"
                  "\t(x0, x1, y0, y1) to set all 4 dimensions"
                  )

        usr_input = input(">> ")
        process_input(yearframe, loopframe, usr_input)

        if loopframe.end: return loopframe.dimensions

def process_input(yearframe, loopframe, usr_input):
    x0, x1, y0, y1 = loopframe.dimensions
    loopframe.run = False
    loopframe.instruct = False

    def proc_error():
        print("Invalid input.")
        loopframe.instruct = True

    if usr_input == 'o':
        subprocess.run(['zathura', yearframe.filepath, '-p', 
                        str(loopframe.pagenum)])
        return
    elif usr_input == 'N':
        loopframe.end = True
        return
    elif usr_input == 'V':
        loopframe.run = True
        return
    elif usr_input == 'h':
        loopframe.instruct = True
        return
    elif usr_input == 'exit':
        exit(1)

    elif len(usr_input) < 3: 
        proc_error()
        return

    elif usr_input[0] == '(' and usr_input[-1] == ')': #eg. (x0, x1, y0, y1)
        dimensions = [d.strip() for d in usr_input[1:-1].split(',')]
        if not all(d.isdigit() for d in dimensions):
            proc_error()
            return
        dimensions = tuple(int(d) for d in dimensions)
        print(dimensions)
        loopframe.dimensions = dimensions
        loopframe.run = True
        return

    elif usr_input[0:2] not in {'x0', 'x1', 'y0', 'y1'}: # catchall error
        proc_error()
        return

    elif usr_input[2] == '+' or usr_input[2] == '-':
        if usr_input[3] != ' ' or not usr_input[4:].isdigit():
            proc_error()
            return
        if usr_input[2] == '+': delta = 1
        else: delta = -1
        change = lambda x: x + int(usr_input[4:]) * delta
    else:
        if usr_input[2] != ' ' or not usr_input[3:].isdigit():
            proc_error()
            return

        change = lambda x: int(usr_input[3:])

    match usr_input[0:2]:
        case 'x0': x0 = change(x0)
        case 'x1': x1 = change(x1)
        case 'y0': y0 = change(y0)
        case 'y1': y1 = change(y1)

    loopframe.dimensions = (x0, x1, y0, y1)
    print(f"Dimensions: ({x0}, {x1}, {y0}, {y1})")

def write_to_tmp(dict_dump):
    with open('tmp.json', 'w') as file:
        json.dump(dict_dump, file, indent=1)

def main():
    format_dict = get_format_dict()

    for y in range(int(YEAR_START), int(YEAR_END) + 1):
        year = str(y) + "-" + str(y + 1)[-2:]
        prior = str(y - 1) + "-" + str(y)[-2:]
        filepath = os.path.join(REPORTS_DIR, REPORT_NAME_FORMAT.format(year=year))

        with open(filepath, 'rb') as file:
            pdf = pdfplumber.open(file)

            yearframe = YearFrame(year, prior, pdf, filepath, format_dict)
            if yearframe.full():
                continue

            print(f'Year: {year}')
            loop_categories(yearframe, format_dict)


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == "year":
        format_dict = get_format_dict()

        y = int(sys.argv[2])
        year = str(y) + "-" + str(y + 1)[-2:]
        prior = str(y - 1) + "-" + str(y)[-2:]
        filepath = os.path.join(REPORTS_DIR, REPORT_NAME_FORMAT.format(year=year))

        print("Year: {year}")

        with open(filepath, 'rb') as file:
            pdf = pdfplumber.open(file)
            yearframe = YearFrame(year, prior, pdf, filepath, format_dict)
            loop_categories(yearframe, format_dict, skip=False)

    else:
        main()
