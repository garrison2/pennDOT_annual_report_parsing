import pdfplumber
import requests
import io

BUSLINES = ['1', '2', '4', '6', '7', '8', '11', '12', '13', '14', '15', '16', '17', '18', '20', '21', '22', '24', '26', '27', '29', '31', '36', '38',
            '39', '40', '41', '43', '44', '48', '51', '53', '54', '55', '56', '57', '58', '59', '60', '64', '65', '67', '69', '71', '74', '75', '77',
            '79', '81', '82', '83', '86', '87', '88', '89', '91', '93', '19L', '28X', '51L', '52L', '53L', '61A', '61B', '61C', '61D', '71A', '71B',
            '71C', '71D', 'BLUE', 'G2', 'G3', 'G31', 'O1', 'O12', 'O5', 'P1', 'P10', 'P12', 'P13', 'P16', 'P17', 'P2', 'P3', 'P67', 'P68', 'P69', 'P7']

def main():
    errors_list = []
    for i in range(len(BUSLINES)):
        busline =BUSLINES[i]
        response = requests.get(f"https://www.rideprt.org/pdfs/{busline}.pdf")
        with io.BytesIO(response.content) as pdf:
            try:
                print(parse_pdf(pdf))
            except Exception as e:
                print(response.url)
                errors_list += [e]

    print('\n\n')
    for e in errors_list:
        print(e)

def parse_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        cropped = cropped_page(pdf)
        text = get_text(cropped)
        cleaned = clean_text(text)
        pdf.close()
        
    return cleaned

def clean_text(text):
    bus_dict = dict()
    name = None
    for line in text:
        if line.split()[0] in BUSLINES:
            name = line.split()[0]
            bus_dict[name] = bus_dict.get(name, [])
            continue

        if name == None:
            raise Exception(f'Name could not be identified.\n{text}')
        neighborhoods = line.split(bytes(b'\xe2\x80\xa2').decode())
        neighborhoods = [nb.strip() for nb in neighborhoods]
        bus_dict[name] += neighborhoods

    return bus_dict

def cropped_page(pdf):
    page = pdf.pages[1]
    chars = page.chars

    start_index = find_effective(page)
    start_char = chars[start_index] # returns the char of E in EFFECTIVE

    x0 = start_char['x1'] - 6 # finds text on left edge of box
    x1 = page.width
    top = start_char['bottom'] # finds bottom of E
    bottom = page.height
    cropped_page = page.within_bbox((x0, top, x1, bottom))

    return cropped_page

def get_text(page):
    text = ['']
    last_y = None
    index = 0
    for c in page.chars:
        if last_y and c['top'] != last_y:
            index += 1
            text.append('')

        last_y = c['top']
        text[index] += (c['text'])

    return text

def find_effective(page):
    chars = page.chars
    for i in range(len(chars)):
        j = 0
        valid = True
        for char_to_check in 'EFFECTIVE':
            if chars[i + j]['text'] != char_to_check:
                valid = False
                break
            j += 1
        if valid:
            return i

if __name__ == '__main__':
    main()
