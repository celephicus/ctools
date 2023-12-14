
import re

def mk_state_name(st_name):
    return '$(STATE_NAME_PREFIX)' + re.sub(r'([a-z])([A-Z])', r'\1_\2', st_name).upper()

class OrderedSet:
    """A minimal ordered set that retains insertion order."""
    def __init__(self, init_els=[]):
        self.elems = []
        for x in list(init_els):
            self.add(x)
    def add(self, elem):
        if elem not in self.elems:
            self.elems.append(elem)
    def discard(self, elem):
        try: self.elems.remove(elem)
        except ValueError: pass

    class SmkOrderedSetIterator:
        def __init__(self, elems):
            self._iter = iter(elems)
        def __next__(self):
            return self._iter.__next__()
    def __iter__(self):
        return self.SmkOrderedSetIterator(self.elems)