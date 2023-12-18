"Some utility methods & classes used throughout smk."
import re

def mk_state_name(st_name):
	"Turn a camelCase state name into a snake_case with the state ident prefix macro."
	return '$(STATE_NAME_PREFIX)' + re.sub(r'([a-z])([A-Z])', r'\1_\2', st_name).upper()

class OrderedSet:
	"""A minimal ordered set that retains insertion order."""
	def __init__(self, init_els=None):
		self.elems = []
		if init_els:
			for x in list(init_els):
				self.add(x)
	def add(self, elem):
		"Add an element only if not already in the set."
		if elem not in self.elems:
			self.elems.append(elem)
	def discard(self, elem):
		"remove an element, no error if not present."
		try:
			self.elems.remove(elem)
		except ValueError:
			pass

	class SmkOrderedSetIterator:     # pylint: disable=too-few-public-methods
		"A little iterator for an OrderedSet class."
		def __init__(self, elems):
			self._iter = iter(elems)
		def __next__(self):
			return self._iter.__next__()
	def __iter__(self):
		return self.SmkOrderedSetIterator(self.elems)
