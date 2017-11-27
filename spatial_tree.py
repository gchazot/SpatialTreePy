class OutOfBounds(Exception):
    pass


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class Rectangle:
    def __init__(self, left, right, bottom, top):
        assert left < right
        assert bottom < top
        self.left = left
        self.right = right
        self.bottom = bottom
        self.top = top

    def __str__(self):
        return "{bottom}:{left}/{top}:{right}".format(**self.__dict__)

    def __contains__(self, point):
        return (self.left <= point.x < self.right and
                self.bottom <= point.y < self.top)

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


class SpatialTree:
    def __init__(self, bounds, max_items_per_leaf=10, leaves=None):
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
