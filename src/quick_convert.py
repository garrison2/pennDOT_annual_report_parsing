a = {'Name':None, 'Service Area Statistics': ['Square Miles', 'Population'], 'Act 44 Fixed Route \nDistribution Factors':['Total Passengers', 'Senior Passengers', 'Revenue Vehicle Miles', 'Revenue Vehicle Hours'], 'Act 44 Operating Assistance':['Section 1513 Allocation', 'Required Local Match'], 'Total Fleet Size':['Motor Bus', 'Commuter Rail Cars', 'Heavy Rail Cars', 'Street Car Rail/Light Rail', 'Trolley Bus', 'Paratransit Vehicles', 'System-wide'], 'Fare Information':['Fixed Route Base', 'Fixed Route Avg', 'Last Base Fare Increase', 'System-wide Increase'], 'Employees':{'Fixed Route Full/Part Time', 'Paratransit Full/Part Time', 'Systemwide Full/Part Time'}, 'Operating Expense':None, 'Operating Funds':None}

import json
with open('format.json', 'r') as file:
    b = json.load(file)

for year in b:
    c = b[year]['categories']
    d = dict()
    for cat in a:
        d[cat] = {'name':c[cat][0], 'box':c[cat][3], 
                  'delim':c[cat][2], 'subheadings':None}
        d[cat]['subheadings'] = dict()
        if a[cat]:
            for subcat in a[cat]:
                name = c[subcat][0]
                delim = c[subcat][2]

                d[cat]['subheadings'][subcat] = {'name':name, 'delim':delim}
        else:
            d[cat].pop('subheadings')


    b[year]['categories'] = d

    b[year]['meta']['boxes'] = dict()

    b[year]['meta']['boxes']['lbox'] = c['lbox']
    b[year]['meta']['boxes']['rbox'] = c['rbox']
    b[year]['meta']['boxes']['tbox'] = c['tbox']
    b[year]['meta']['boxes']['lchart'] = c['lchart']
    b[year]['meta']['boxes']['rchart'] = c['rchart']


with open('new_tmp.json', 'w') as file:
    json.dump(b, file, indent=1)



