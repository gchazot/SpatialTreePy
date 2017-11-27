import fileinput
import sys
from spatial_tree import Point, Rectangle, SpatialTree


def debug(*args, **kwargs):
    kwargs.update(file=sys.stderr)
    return print(*args, **kwargs)


def get_files():
    yield "code_challenge/20170901_080005.csv"


def distance(latitude_1, longitude_1, latitude_2, longitude_2):
    from math import radians, cos, sin, asin, sqrt

    EARTH_RADIUS_KM = 6371.0
    lat_1_rad = radians(latitude_1)
    lon_1_rad = radians(longitude_1)
    lat_2_rad = radians(latitude_2)
    lon_2_rad = radians(longitude_2)
    u = sin( (lat_2_rad - lat_1_rad) / 2 )
    v = sin( (lon_2_rad - lon_1_rad) / 2 )

    return 2 * EARTH_RADIUS_KM * asin( sqrt( u**2 + cos(lat_1_rad) * cos(lat_2_rad) * (v**2) ) )


class Flight(Point):
    def __init__(self, call_sign, latitude, longitude):
        super().__init__(latitude, longitude)
        self.call_sign = call_sign

    @staticmethod
    def create(line):
        fields = line.split(',')
        try:
            lat = float(fields[1])
            lon = float(fields[2])
        except ValueError:
            debug("Not a flight: " + line)
            return None
        return Flight(fields[0], lat, lon)

    def distance(self, other):
        return distance(self.x, self.y, other.x, other.y)


def solution1():
    flights = []
    for line in fileinput.input(files=get_files()):
        flight = Flight.create(line)
        if flight is None:
            continue
        flights.append(flight)

    for f1 in flights:
        closest_flight = None
        closest_distance = None
        for f2 in flights:
            if f1 == f2:
                continue
            dist = f1.distance(f2)
            if closest_distance is None or dist < closest_distance:
                closest_distance = dist
                closest_flight = f2
        print("{} {} {}km".format(f1.call_sign, closest_flight.call_sign, closest_distance))


def solution2():
    index = SpatialTree(Rectangle(-90.0, 90.0, -180.0, 180.0))
    for line in fileinput.input(files=get_files()):
        flight = Flight.create(line)
        if flight is None:
            continue
        index.add(flight)

    for flight in index:
        closest = index.closest(flight)
        if closest is not None:
            print("{} {} {:.1f} KM".format(
                flight.call_sign,
                closest.call_sign,
                flight.distance(closest)
            ))
        else:
            debug("No Closest {}".format(flight.call_sign))


if __name__ == "__main__":
    solution2()

