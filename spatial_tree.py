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

    def distance_straight(self, other):
        return 2 * self.EARTH_RADIUS_KM * math.sin(self.distance_rad(other) / 2)


class Rectangle:
    def __init__(self, bottom, left, top, right):
        assert bottom <= top
        assert left <= right
        self.bottom = bottom
        self.left = left
        self.top = top
        self.right = right

    def __str__(self):
        return "{bottom}:{left}/{top}:{right}".format(**self.__dict__)

    def __contains__(self, point):
        return (self.bottom <= point.lat < self.top and
                self.left <= point.lon < self.right)

    def intersects(self, other):
        return (self.bottom <= other.top and
                other.bottom <= self.top and
                self.left <= other.right and
                other.left <= self.right)

    def corners(self):
        return (Point(self.bottom, self.left),
                Point(self.bottom, self.right),
                Point(self.top, self.left),
                Point(self.top, self.right))

    def centric_split(self):
        """Splits a rectangle in 4 equal rectangles
        @:return a list of the new rectangles"""
        middle_lat = (self.top + self.bottom) / 2.0
        middle_lon = (self.right + self.left) / 2.0
        return [
            Rectangle(self.bottom, self.left, middle_lat, middle_lon),
            Rectangle(self.bottom, middle_lon, middle_lat, self.right),
            Rectangle(middle_lat, self.left, self.top, middle_lon),
            Rectangle(middle_lat, middle_lon, self.top, self.right)
            ]


class ClosestSearchResult:
    def __init__(self, point):
        self.point = point
        self.closest = None
        self.closest_dist = None

    def distance(self, other_point):
        return self.point.distance_rad(other_point)

    def update(self, other_point):
        distance = self.distance(other_point)
        if self.closest is None or distance < self.closest_dist:
            self.closest = other_point
            self.closest_dist = distance

    def delta_lon(self, lon):
        angle = abs(self.point.lon - lon)
        if angle > math.pi:
            angle = 2 * math.pi - angle
        return angle

    def dist_to_meridian(self, lon):
        return math.asin(math.cos(self.point.lat) * math.sin(self.delta_lon(lon)))

    def lat_at_meridian(self, lon):
        return math.pi / 2 - math.atan(math.cos(self.delta_lon(lon)) / math.tan(abs(self.point.lat)))

    def intercept_meridian(self, lon):
        return Point(self.lat_at_meridian(lon), lon)

    def intersects(self, bounds):
        if self.closest is None or self.point in bounds:
            return True

        if bounds.left <= self.point.lon <= bounds.right:
            min_dist = min(abs(self.point.lat - bounds.top),
                           abs(self.point.lat - bounds.bottom))
        elif (bounds.left + math.pi) % math.pi <= (self.point.lon + math.pi) % math.pi <= (bounds.right + math.pi) % math.pi:
            min_dist = min(math.pi - abs(self.point.lat + bounds.top),
                           math.pi - abs(self.point.lat + bounds.bottom))
        else:
            closest_to_left = self.intercept_meridian(bounds.left)
            closest_to_right = self.intercept_meridian(bounds.right)

            points = list(bounds.corners())
            points.append(closest_to_left)
            points.append(closest_to_right)

            min_dist = min(list(map(self.distance, points)))

        return min_dist <= self.closest_dist


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
        new_leaves = [SpatialLeaf(rect, self.max_items) for rect in self.bounds.centric_split()]
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
                break
        for leaf in self.leaves:
            if result.point not in leaf:
                if result.intersects(leaf.bounds):
                    leaf.search_closest(result)

