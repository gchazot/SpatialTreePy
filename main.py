import fileinput
import sys
from abc import ABCMeta, abstractmethod

import collections
import rtree

from spatial_tree import Point, Rectangle, SpatialTree, ClosestSearchResult
import timeit


def debug(*args, **kwargs):
    kwargs.update(file=sys.stderr)
    return print(*args, **kwargs)


def get_files():
    yield "data/20170901_080005.csv"


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
            return None
        return Flight(fields[0], lat, lon)


def format_line(flight_1, flight_2):
    return "{:8} {:8} {:8.2f} {:8.2f}".format(
        flight_1.call_sign,
        flight_2.call_sign,
        flight_1.distance_geodetic(flight_2),
        flight_1.distance_geodetic_old(flight_2))


class Solution(metaclass=ABCMeta):
    def run(self, output_file=None):
        self.parse()
        self.solve_all(output_file)

    @abstractmethod
    def parse(self):
        pass

    def solve_all(self, output_file=None):
        for target, closest in self.solve_one():
            if output_file is not None:
                line = self.make_line(target, closest)
                print(line, file=output_file)

    @abstractmethod
    def solve_one(self):
        return collections.Iterable()

    def make_line(self, target, closest):
        return format_line(self.make_flight(target), self.make_flight(closest))

    @abstractmethod
    def make_flight(self, flight):
        return Flight("", 0, 0)


class WithForForLoop(Solution):
    def __init__(self):
        self.flights = []

    def parse(self):
        for line in fileinput.input(files=get_files()):
            flight = Flight.create(line)
            if flight is None:
                continue
            self.flights.append(flight)

    def solve_one(self):
        for f1 in self.flights:
            closest_flight = None
            closest_distance = None
            for f2 in self.flights:
                if f1 == f2:
                    continue
                distance = f1.distance_rad(f2)
                if closest_distance is None or distance < closest_distance:
                    closest_distance = distance
                    closest_flight = f2
            yield (f1, closest_flight)

    def make_flight(self, flight):
        return flight


class WithSpatialIndex(Solution):
    def __init__(self):
        self.index = SpatialTree(
            Rectangle(-90.0, 90.0, -180.0, 180.0)
        )

    def parse(self):
        for line in fileinput.input(files=get_files()):
            flight = Flight.create(line)
            if flight is None:
                continue
            self.index.add(flight)

    def solve_one(self):
        for flight in self.index:
            result = ClosestSearchResult(flight)
            self.index.search_closest(result)
            yield (flight, result.closest)

    def make_flight(self, flight):
        return flight


class WithRtree(Solution):
    def __init__(self):
        self.index = rtree.index.Index()
        self.flights = []

    @staticmethod
    def coordinates(flight):
        return [flight.lat, flight.lon, flight.lat, flight.lon]
        
    def parse(self):
        file_input = fileinput.input(files=get_files())
        for n, line in enumerate(file_input):
            flight = Flight.create(line)
            if flight is None:
                continue
            self.flights.append(flight)
            location = WithRtree.coordinates(flight)
            self.index.insert(n, location)

    def solve_one(self):
        for n, flight in enumerate(self.flights):
            location = WithRtree.coordinates(flight)
            closest_answers = self.index.nearest(location)
            for closest in closest_answers:
                yield n-1, closest-1

    def make_flight(self, flight):
        return self.flights[flight]


if __name__ == "__main__":
    # with open("solution2.txt", "w") as output:
    #    WithSpatialIndex().run(output)
    # WithSpatialIndex().run(sys.stdout)
    WithRtree().run(sys.stdout)
