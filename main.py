import os
import random
from xml.dom import minidom

import numpy as np
import pandas
import pandas as pd
import traci


def initialize(grids=1, length=100):
    os.system("netgenerate --grid --grid.number=" + str(grids) + " --grid.length=" + str(
        length) + " --output-file=grid.net.xml")


def generate_simulation():
    # initialize(5, 50)
    # os.system('''python3 C:/sumo/tools/randomTrips.py -n grid.net.xml -o routes.xml --begin 0 --end 1 --flows 40''')
    # os.system( "jtrrouter --route-files=routes.xml --net-file=grid.net.xml --output-file=grid.rou.xml --begin 0 --end 6000 --accept-all-destinations")
    # os.system("python3 C:/sumo/tools/generateContinuousRerouters.py -n grid.net.xml --end 1000 -o rerouter.add.xml")

    generate_parking_lots()
    sumo_binary = "sumo-gui"
    #sumo_binary = 'sumo-cmd'
    sumo_cmd = [sumo_binary, "-c", "grid.sumocfg"]
    sumo_cmd.append("-d")
    sumo_cmd.append("200")
    traci.start(sumo_cmd)
    # vehicles = pandas.read_xml('grid.parking_routes.rou.xml', xpath='.//vehicle', attrs_only=True)
    parkingStop = pd.read_xml('parkinglots.xml', xpath='.//parkingArea', attrs_only=True)

    pkAreaids = parkingStop['id'].tolist()
    step = 0
    while step < 200:
        step += 1
        traci.simulationStep()
        veh_ids = traci.vehicle.getIDList()
        for v in veh_ids:
            try:
                traci.vehicle.rerouteParkingArea(v,pkAreaids[5])
            except:
                pass
    traci.close()
    plot_data()



def generate_parking_lots():
    edges = pandas.read_xml('grid.net.xml', xpath='''.//edge[not(starts-with(@id,':'))]''', attrs_only=True)
    lanes = pandas.read_xml('grid.net.xml', xpath='''.//lane[not(starts-with(@id,':'))]''', attrs_only=True)

    parkinglots = pd.DataFrame(columns=['id', 'lane', 'startPos', 'endPos', 'roadsideCapacity'])
    for i in range(len(edges['id'])):
        dict = {'id': 'pl%s' % edges['id'][i], 'lane': '%s_0' % edges['id'][i], 'startPos': "0",
                'endPos': lanes['length'][i], 'roadsideCapacity': str(int(float(lanes['length'][i]) / 6.0))}
        parkinglots = parkinglots.append(dict, ignore_index=True)

    columns = parkinglots.columns.tolist()
    xml = parkinglots.to_xml(root_name='additionals', row_name='parkingArea', attr_cols=columns, index=False)
    with open('parkinglots.xml', 'w') as f:
        f.write(xml)
    # os.system( "python3  C:/this/sumo/tools/generateParkingAreas.py -n grid.net.xml -o parkinglots.xml -L 4 -l 2 -r --prefix pl")
    # parkinglots = pd.read_xml('parkinglots.xml',xpath='.//parkingArea')
    assign_vehicles()
    createInductionLoops(edges, lanes)


def assign_vehicles():
    vehicles = pandas.read_xml('grid.rou.xml', xpath='.//vehicle', attrs_only=True)
    routes = pandas.read_xml('''grid.rou.xml''', xpath=".//route", attrs_only=True)
    temp_ids = []
    stop = pd.DataFrame(columns=['parkingArea', 'duration'])
    for x in routes['edges']:
        edges = x.split()
        rand_idx = np.random.choice(a=range(0, len(edges)), size=1)[0]
        stop = stop.append({'parkingArea': 'pl' + edges[rand_idx], 'duration': '100'}, ignore_index=True)
        #temp_ids.append(rand_idx)

    parkingRoutes = pd.concat([vehicles, routes, stop], axis=1)
    # cutting out the extra lines from the merge
    parkingRoutes = parkingRoutes[parkingRoutes['parkingArea'].notna()]
    parkingRoutes = parkingRoutes[parkingRoutes['id'].notna()]

    parking_routes = minidom.Document()
    root = parking_routes.createElement('routes')
    parking_routes.appendChild(root)

    for index, row in parkingRoutes.iterrows():
        vehicles_xml = parking_routes.createElement('vehicle')
        vehicles_xml.setAttribute('id', str(row['id']))
        vehicles_xml.setAttribute('depart', str(row['depart']))
        vehicles_xml.setAttribute('reroute', 'true')
        root.appendChild(vehicles_xml)
        routes_xml = parking_routes.createElement('route')
        routes_xml.setAttribute('edges', str(row['edges']))
        vehicles_xml.appendChild(routes_xml)
        stop_xml = parking_routes.createElement('stop')
        stop_xml.setAttribute('parkingArea', str(row["parkingArea"]))
        stop_xml.setAttribute('duration', str(row['duration']))
        vehicles_xml.appendChild(stop_xml)

    with open('grid.parking_routes.rou.xml', 'w') as f:
        f.write(parking_routes.toprettyxml())
    # os.system("python3  C:/sumo/tools/generateParkingAreaRerouters.py -n ./grid.net.xml -a ./parkinglots.xml --max-distance-alternatives 10000 --max-distance-visibility-true 1000 -o ./grid.parking_reroutes.add.xml")


def createInductionLoops(edges, lanes):
    inductionLoops = pd.DataFrame(columns=['id', 'lane', 'pos', 'freq', 'file'])

    for i in range(len(edges)):
        dict = {'id': 'il%s' % edges['id'][i], 'lane': '%s_0' % edges['id'][i], 'pos': "30", 'freq': '100',
                'file': 'data.out.xml'}
        inductionLoops = inductionLoops.append(dict, ignore_index=True)
    columns = inductionLoops.columns.tolist()
    xml = inductionLoops.to_xml(root_name='additionals', row_name='inductionLoop', attr_cols=columns)
    with open('induction.loops.xml', 'w') as f:
        f.write(xml)


import matplotlib.pyplot as plt


def plot_data():
    data = pd.read_xml('data.out.xml', xpath='.//interval', attrs_only=True)
    occ = data['flow'].tolist()
    mean = data['harmonicMeanSpeed '].tolist()
    plt.plot(occ, mean, 'ro')
    plt.xlabel('flow ')
    plt.ylabel('harmonic mean speed m/s')
    plt.show()


if __name__ == '__main__':
    generate_simulation()
