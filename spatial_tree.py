import math


class OutOfBounds(Exception):
    pass


class Point:
    def __init__(self, latitude, longitude):
        self.lat = math.radians(latitude)
        self.lon = math.radians(longitude)

    def distance_rad(self, other):
        return math.acos(
            math.sin(self.lat) * math.sin(other.lat) +
            math.cos(self.lat) * math.cos(other.lat) * math.cos(self.lon - other.lon)
        )

    def distance_deg(self, other):
        return math.degrees(self.distance_rad(other))

    EARTH_RADIUS_KM = 6371.0

    def distance_geodetic(self, other):
        return self.EARTH_RADIUS_KM * self.distance_rad(other)

    def distance_geodetic_old(self, other):
        u = math.sin((other.lat - self.lat) / 2)
        v = math.sin((other.lon - self.lon) / 2)
        w = math.sqrt(u ** 2 + math.cos(self.lat) * math.cos(other.lat) * (v ** 2))
        return 2 * self.EARTH_RADIUS_KM * math.asin(w)


class Rectangle:
    def __init__(self, left, right, bottom, top):
        assert left <= right
        assert bottom <= top
        self.left = left
        self.right = right
        self.bottom = bottom
        self.top = top

    def __str__(self):
        return "{bottom}:{left}/{top}:{right}".format(**self.__dict__)

    def __contains__(self, point):
        return (self.left <= point.lat < self.right and
                self.bottom <= point.lon < self.top)

    def intersects(self, other):
        return (self.left <= other.right and
                other.left <= self.right and
                self.bottom <= other.top and
                other.bottom <= self.top)

    def centric_split(self):
        """Splits a rectangle in 4 equal rectangles
        @:return a list of the new rectangles"""
        middle_x = (self.right + self.left) / 2.0
        middle_y = (self.top + self.bottom) / 2.0
        return [
            Rectangle(self.left, middle_x, self.bottom, middle_y),
            Rectangle(self.left, middle_x, middle_y, self.top),
            Rectangle(middle_x, self.right, self.bottom, middle_y),
            Rectangle(middle_x, self.right, middle_y, self.top)
            ]


class ClosestSearchResult:
    def __init__(self, point):
        self.point = point
        self.bounds = Rectangle(-math.inf, math.inf, -math.inf, math.inf)
        self.closest = None
        self.closest_dist = None

    def update(self, other_point):
        distance = self.point.distance_rad(other_point)
        if self.closest is None or distance < self.closest_dist:
            self.closest = other_point
            self.closest_dist = distance
            box_size = self.point.distance_rad(other_point)
            self.bounds = Rectangle(self.point.lat - box_size, self.point.lat + box_size,
                                    self.point.lon - box_size, self.point.lon + box_size)


class SpatialLeaf:
    def __init__(self, bounds, max_items):
        self.bounds = bounds
        self.points = []
        self.max_items = max_items

    def __str__(self):
        return "Leaf [{}] {}/{}".format(self.bounds, self.count(), self.max_items)

    def add(self, point):
        if point not in self.bounds:
            raise OutOfBounds()
        self.points.append(point)

    def __contains__(self, point):
        return point in self.bounds

    def intersects(self, other):
        return self.bounds.intersects(other)

    def split(self):
        new_leaves = [SpatialLeaf(r, self.max_items) for r in self.bounds.centric_split()]
        for point in self.points:
            for leaf in new_leaves:
                if point in leaf:
                    leaf.add(point)
                    break
        return new_leaves

    def must_split(self):
        return self.count() > self.max_items

    def count(self):
        return len(self.points)

    def max_count(self):
        return self.count()

    def max_depth(self):
        return 1

    def __iter__(self):
        return self.points.__iter__()

    def search_closest(self, result):
        for point in self.points:
            if point == result.point:
                continue
            result.update(point)


class SpatialTree:
    def __init__(self, bounds, max_items_per_leaf=8, leaves=None):
        self.bounds = bounds
        if leaves is None:
            leaves = SpatialLeaf(self.bounds, max_items_per_leaf).split()
        self.leaves = leaves

    def __str__(self):
        return "Tree [{}]".format(self.bounds)

    def add(self, point):
        split = None
        for i, leaf in enumerate(self.leaves):
            if point in leaf:
                leaf.add(point)
                if leaf.must_split():
                    split = i
                break

        if split is not None:
            new_leaf = self.split_of(self.leaves[split])
            self.leaves[split] = new_leaf

    def __contains__(self, point):
        return point in self.bounds

    def intersects(self, other):
        return self.bounds.intersects(other)

    @staticmethod
    def split_of(leaf):
        return SpatialTree(leaf.bounds, leaf.max_items, leaf.split())

    def must_split(self):
        return False

    def count(self):
        return sum((leave.count() for leave in self.leaves))

    def max_count(self):
        return max(leaf.max_count() for leaf in self.leaves)

    def max_depth(self):
        return max(leaf.max_depth() for leaf in self.leaves) + 1

    def __iter__(self):
        for leaf in self.leaves:
            for point in leaf:
                yield point

    def search_closest(self, result):
        for leaf in self.leaves:
            if result.point in leaf:
                leaf.search_closest(result)
        for leaf in self.leaves:
            if result.point not in leaf:
                if leaf.intersects(result.bounds):
                    leaf.search_closest(result)

