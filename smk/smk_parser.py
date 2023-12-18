"""Quite a useful generic XML data parser with simple validation. Elements are represented as classes, that can validate
	their attributes and contained elements.
"""

import xml.parsers.expat
import sys, re
import smk_utils

# Disable warnings as we dynamically create attributes.
# pylint: disable=no-member,access-member-before-definition,attribute-defined-outside-init

# Generic Stuff
class NodeError(Exception):
	"""Exception raised by Node subclasses when they cannot initialise themselves from attributes supplied.
		The lineno is supplied by the parser when it catches a NodeError exception and is then rethrown. """
	def __init__(self, msg, lineno=0):
		Exception.__init__(self, msg)
		self.msg, self.lineno = msg, lineno

class Node:
	"Base class for a node or XML element."
	OPT_MANDATORY, OPT_OPTIONAL, OPT_MULTI = list(range(3))

	# Maps attribute name (also the attribute if the class) to a tuple of (flag, validator). Flag may be one of the
	#  OPT_MANDATORY or OPT_OPTIONAL, and the validator function returns a value of the correct type or raises an
	#  exception.
	ATTRIBUTES = {}

	# Maps child element name (also the attribute if the class) to a tuple of (flag, validator). Flag may be one of the
	#  OPT_MANDATORY, OPT_OPTIONAL or OPT_MULTI and the validator function returns a value of the correct type or raises
	#  an exception. If the validator is a class inheriting from Node, then the child's data is read from the XML stream.
	CHILD_ELEMENTS = {}

	# List attribute for content and validator function.
	CONTENT = (None, None)  # No content allowed.

	def __init__(self, root, parent, attr, lineno):
		"Construct with the given parent and attributes. Raise an exception if things are not well."
		self.root, self.parent = root, parent
		self.lineno = lineno
		if self.CONTENT[0]:
			setattr(self, self.CONTENT[0], self.CONTENT[1]('')) # pylint: disable=not-callable
		self.characters = []
		self.simple_attribute = None
		self._add_attributes(attr)
		self._check_extra_attributes(attr)
		self._process_child_element_map()
	def is_root(self):
		"Check if node is the root of our tree. Typically the root node is really only a container or is very limited."
		return self.root is self.parent
	def _check_extra_attributes(self, attrs):
		for attr_name in attrs:
			if attr_name not in self.ATTRIBUTES:
				raise NodeError(f"extra attribute `{attr_name}' for element `{self.node_name()}'") # ** Tested
	def _add_attributes(self, attr):
		for attr_name, attr_def in list(self.ATTRIBUTES.items()):
			flags, validator = attr_def
			if attr_name not in attr:
				if flags == Node.OPT_MANDATORY:
					raise NodeError(f"missing attribute `{attr_name}' for element `{self.node_name()}'") # ** Tested
				setattr(self, attr_name, validator(''))	# Set default value from validator.
			else:
				try:
					setattr(self, attr_name, validator(attr[attr_name]))
				except Exception as exc:
					raise NodeError(
					  f"bad attribute value {attr_name}=`{attr[attr_name]}' [{str(exc)}] for element `{self.node_name()}'"
					  ) from exc # ** Tested
	def _process_child_element_map(self):
		for child_name, (flags, validator_func) in self.CHILD_ELEMENTS.items():
			if flags in (Node.OPT_MANDATORY, Node.OPT_OPTIONAL):
				setattr(self, child_name, None) # We use the presence of the None value to verify that this child is present.
			elif flags == Node.OPT_MULTI:
				setattr(self, child_name, [])

			# If we want an element to contain itself, the class name must be given as a validator. But the class isn't
			#  defined yet, so it is given as a string, which must be eval'ed.
			if isinstance(validator_func, str):
				self.CHILD_ELEMENTS[child_name] = flags, eval(validator_func) # pylint: disable=eval-used

	@classmethod
	def node_name(cls):
		"Returns name of node or element, which is class name in lower case."
		return cls.__name__.lower()
	def process_character_data(self, content):
		"Accept character data when in an element."
		self.characters.append(content)
	def element_begin(self, name, attrs, lineno):
		"Do housekeeping at the start of a particular element definition."
		if self.simple_attribute:
			NodeError(f"element `{name}' cannot be nested within element `{self.simple_attribute}'")  # ** Tested.
		try:
			flags, validator = self.CHILD_ELEMENTS[name]
		except KeyError as exc:
			raise NodeError(f"element `{name}' cannot be nested within element `{self.node_name()}'") from exc  # ** Tested

		# Now decide if we have a subclass (not an _instance_) of Node. Is there a better way to do this?
		try:
			is_complex_element = issubclass(validator, Node)
		except TypeError:
			is_complex_element = False
		if is_complex_element:
			new_child = validator(self.root, self, attrs, lineno) # This element's parent is self.
			if flags in (Node.OPT_MANDATORY, Node.OPT_OPTIONAL):
				if getattr(self, name):
					raise NodeError(f"element `{name}' may not appear more than once as a child of `{self.node_name()}'") # ** Tested.
				setattr(self, name, new_child)
			elif flags == Node.OPT_MULTI:
				getattr(self, name).append(new_child)
			return new_child

		self.simple_attribute = name
		return None

	def element_end(self, name):
		"Do housekeeping at the end of a particular element definition."
		if self.simple_attribute:
			if self.simple_attribute != name:
				raise NodeError(f"internal error: close simple element: expected `{self.simple_attribute}', got `{name}'") # Not tested.
			flags, validator = self.CHILD_ELEMENTS[name]
			validated_value = validator(self._get_character_data())
			if flags in (Node.OPT_MANDATORY, Node.OPT_OPTIONAL):
				if getattr(self, name):
					raise NodeError(f"element `{name}' may not appear more than once as a child of `{self.parent.node_name()}'")
				setattr(self, self.simple_attribute, validated_value)
			else:
				getattr(self, name).append(validated_value)
			self.simple_attribute = None
			return False

		if name != self.node_name():
			raise NodeError(f"internal error: close element for <{self.node_name()}> _really_unexpected, got <{name}>")  # Not tested.

		# We must have a subclass of Node...
		self._check_mandatory_present(self.CHILD_ELEMENTS)
		content = self._get_character_data().strip()
		if self.CONTENT[0]:     # If this element can have content...
			try:
				setattr(self, self.CONTENT[0], self.CONTENT[1](content)) # pylint: disable=not-callable
			except Exception as exc:
				raise NodeError(f"content error {exc} for element `{self.node_name()}'") from exc # Not tested.
		else:   # Content illegal.
			if content:
				raise NodeError(f"content illegal for element `{self.node_name()}'") # ** Tested
		self.validate()
		return True

	def validate(self):
		"Check that the object is internally consistent after building."
		pass
	def _check_mandatory_present(self, attr_dict):
		for k in [k for (k, v) in list(attr_dict.items()) if v[0] == Node.OPT_MANDATORY]:
			try:
				getattr(self, k)
			except AttributeError as exc:
				raise NodeError(f"mandatory attribute `{k}' was not present") from exc # ** Not Tested.
	def _get_character_data(self):
		char_data = ''.join(self.characters)
		self.characters = []
		return char_data
	def __str__(self):
		strs = []
		self.dump(strs)
		return '\n'.join(strs)
	def dump(self, strs, depth=1):
		"Return a readable representation. More readable than XML anyway..."
		strs.append('  ' * (depth-1) + f'<<{self.node_name()}>>')
		all_attrs = [k for k in list(self.ATTRIBUTES.keys()) + [self.CONTENT[0]] + list(self.CHILD_ELEMENTS.keys()) if k]
		for attr_name, attr_value in [(k, getattr(self, k)) for k in all_attrs]:
			if isinstance(attr_value, list):
				if attr_value and isinstance(attr_value[0], Node):
					for val in attr_value:
						val.dump(strs, depth+1)
				else:
					strs.append('  ' * depth + f"{attr_name} = `{attr_value}'")
			else:
				if isinstance(attr_value, Node):
					attr_value.dump(strs, depth+1)
				else:
					strs.append('  ' * depth + f"{attr_name} = `{attr_value}'")
	__repr__ = __str__
	def to_xml(self, ostream, depth=1):		# pylint: disable=too-many-branches
		"Spit out a formatted XML version of the data."
		indent = '  ' * (depth-1)
		ostream.write(indent + f'<{self.node_name()}')

		# Emit attributes.
		for attr_name in self.ATTRIBUTES:
			attr_value = getattr(self, attr_name)
			assert isinstance(attr_value, str) # ATTRIBUTES are always strings.
			ostream.write(f" {attr_name}='{attr_value}'")

		# If this node has no child elements and no content, close the tag now.
		if not self.CHILD_ELEMENTS and not self.CONTENT[0]:
			ostream.write('/>\n')

		else:  # We know that it has either content or child elements.
			ostream.write('>')

			if self.CONTENT[0]:     # Emit content.
				contents = getattr(self, self.CONTENT[0])
				if isinstance(contents, str):
					ostream.write(contents)
				else:
					ostream.write(' '.join(contents)) # Assume some sort of sequence.

			# Emit attributes.
			if self.CHILD_ELEMENTS: # New line for child elements.
				ostream.write('\n')
				for child_el_name in self.CHILD_ELEMENTS:
					el_guts = getattr(self, child_el_name)
					if el_guts is None:
						ostream.write(indent + f'  <{child_el_name}/>\n')
					elif isinstance(el_guts, str):
						ostream.write(indent + f'  <{child_el_name}>{el_guts}</{child_el_name}>\n')
					elif isinstance(el_guts, Node):
						el_guts.to_xml(ostream, depth+1)
					elif isinstance(el_guts, list):
						for guts in el_guts:
							guts.to_xml(ostream, depth+1)
					else:		# Assume some sort of sequence.
						ostream.write(indent + f"  <{child_el_name}>{' '.join(el_guts)}</{child_el_name}>\n")

				ostream.write(indent + f'</{self.node_name()}>\n')
			else:
				ostream.write(f'</{self.node_name()}>\n')

class XmlSerialiser:		# pylint: disable=too-few-public-methods
	"""A cheesy little xml serialiser/deserialiser."""
	def __init__(self, root_type):
		self.xml_parser = xml.parsers.expat.ParserCreate()
		self.xml_parser.StartElementHandler = self._start_element
		self.xml_parser.EndElementHandler = self._end_element
		self.xml_parser.CharacterDataHandler = self._process_character_data
		self.current = None
		self.root_type = root_type
	def _start_element(self, name, attrs):
		str_attrs = {str(k): str(v) for(k, v) in list(attrs.items())}
		str_name = str(name)
		if self.current is None:
			if self.root_type.node_name() == str_name:
				self.current = self.root_type(None, None, str_attrs, self.xml_parser.CurrentLineNumber)
				self.current.root = self.current
			else:
				raise NodeError(f"unknown root element: `{str_name}'") # ** Tested
		else:
			new_child = self.current.element_begin(str(str_name), str_attrs, self.xml_parser.CurrentLineNumber)
			if new_child:
				self.current = new_child
	def _end_element(self, name):
		# Not sure exactly what this does!
		if self.current.element_end(str(name)) and self.current.parent:
			self.current = self.current.parent
	def _process_character_data(self, content):
		self.current.process_character_data(str(content))
	def parse(self, xml_data):
		"Parse a machine description from a string."
		try:
			self.xml_parser.Parse(xml_data, 1)
		except xml.parsers.expat.ExpatError as exc: # XML parse error.
			raise NodeError('XML: ' + str(exc)) from exc
		except NodeError as exc: # Syntax error...
			if not exc.lineno:  # If lineno not given then fill in from the parser.
				exc.lineno = self.xml_parser.CurrentLineNumber
			raise exc                               # ** Tested

# SMK Parser Stuff.
def mk_set(text):
	"Return an ordered set made from the words in the input."
	return smk_utils.OrderedSet(text.split())
def validate_name(name):
	"Is the input string a valid name?"
	if not re.match(r'(?i)[a-z_][a-z0-9_]*$', name):
		raise ValueError(f"name `{name}' illegal") # ** Tested
	return name
def validate_names(names):
	"Is the set of words all valid names?"
	namelist = names.split()
	for name in namelist:
		try:
			validate_name(name)
		except ValueError as exc:
			raise ValueError(f"names `{names}' illegal") from exc
	return namelist

class Init(Node):
	"Any State element can have an Init to transition to a substate."
	CONTENT = ('action', lambda n: n.strip())
	ATTRIBUTES = {'target': (Node.OPT_MANDATORY, validate_name)}

class Entry(Node):
	"Any State element can have an Entry to define actions on entry."
	CONTENT = ('action', lambda n: n.strip())

class Exit(Entry):
	"Any State element can have an Exit to define actions on exit."

class Transition(Node):
	"Element to define action on receiving an event. Bad name, it might not transition at all."
	CONTENT = ('action', lambda n: n.strip())
	ATTRIBUTES = {
	  'event': (Node.OPT_MANDATORY, validate_names),
	  'target': (Node.OPT_OPTIONAL, lambda n: n.strip()),
	  'guard': (Node.OPT_OPTIONAL, lambda n: n.strip()),
	}
	def validate(self):
		for event_name in self.event:
			self.root.event_list.add(event_name)    # Add each event to set in machine.
		#self.root.event_list.add(self.event)
		# We could check for an internal transition with no action, but this is valid as it allows a substate to ignore
		#  events that *are* handled by a superstate.
		# if not self.target and not self.action:
		#     raise NodeError("Degenerate transition %s does nothing", self)

class NodeWithInitTransition(Node):
	"Abstract base class to capture that State & Machine elements can both have Init elements."
	def get_superstates(self):
		"Return list of enclosing states for this Node. Does not include Machine node at root."
		superstates = [self]
		while not superstates[-1].is_root():
			superstates.append(superstates[-1].parent)
		return superstates

	def get_init_actions_state(self):
		"Return tuple (list of init/entry actions, destination_state) for the given node (Machine or State)."
		action_nodes = []
		node = self

		# Do init actions until we reach a substate with no init transition.
		while node.init:
			action_nodes.append(node.init)
			n = node.root.state_map[node.init.target]
			nodes_entered = []
			while n.name != node.name:
				nodes_entered.insert(0, n.entry)
				n = n.parent
			node = node.root.state_map[node.init.target]
			action_nodes += nodes_entered

		return [a.action for a in action_nodes if a], node # Remove all empty actions.

class State(NodeWithInitTransition):
	"The big one. It's all about states really."
	ATTRIBUTES = {
	  'name': (Node.OPT_MANDATORY, validate_name),
	}
	CHILD_ELEMENTS = {
	  'init': (Node.OPT_OPTIONAL, Init),
#      'history': (Node.OPT_OPTIONAL, History), # History & Init cannot occur together.
	  'entry': (Node.OPT_OPTIONAL, Entry),
	  'exit': (Node.OPT_OPTIONAL, Exit),
	  'transition': (Node.OPT_MULTI, Transition),
	  'state': (Node.OPT_MULTI, "State"), # Allow States to contain States.
	}
	def __init__(self, *args):
		super().__init__(*args)

		# Add to the root's state map, which is the primary data structure.
		if self.name in self.root.state_map:
			raise NodeError(f"duplicate state name `{self.name}'") # ** Tested.
		self.root.state_map[self.name] = self
	def validate(self):
		# Verify that all transition have distinct event signatures.
		# Also verifies that at most one transition for each event has no guard.
		trans = smk_utils.OrderedSet()
		for ttt in self.transition:
			trans_sig = (ttt.event, ttt.guard)
			if trans_sig in trans:
				raise NodeError(f"transition with signature {trans_sig.event}[{trans_sig.guard} duplicated") # ** Tested.
			trans.add(trans_sig)

		# Verify that initial transition does not target self.
		if self.init and self.init.target == self.name:
			raise NodeError(f"initial transition for {self.name} cannot target self") # ** Tested.

		# Verify that history & init are not both present.
#        if self.init and self.history:
#            raise NodeError("cannot have an initial transition and a history in the same state %s" % self.name)

class Machine(NodeWithInitTransition):
	"Top element in state machine description. Really just a container for states."
	ATTRIBUTES = {
	  'name': (Node.OPT_MANDATORY, validate_name),
	}
	strip = lambda s: s.strip()
	CHILD_ELEMENTS = {
	  'property': (Node.OPT_MULTI, strip),
	  'include': (Node.OPT_OPTIONAL, strip),
	  'code': (Node.OPT_OPTIONAL, strip),
	  'init': (Node.OPT_OPTIONAL, Init),
	  'state': (Node.OPT_MULTI, State),
	}
	def __init__(self, root, parent, attrs, lineno): # pylint: disable=unused-argument
		super().__init__(None, None, attrs, lineno) # Note parent & root set to nil, as we _are_ the root.

		# We build a list in the machine of all states as we parse the input, allows us to detect duplicated states.
		self.state_map = {}

		# And a set of events.
		self.event_list = smk_utils.OrderedSet()
	def validate(self):	# pylint: disable=too-many-branches
		# Verify target state for all transitions.
		for state in list(self.state_map.values()):
			for trans in state.transition:
				if trans.target and trans.target not in self.state_map:        # Internal transitions have a nil target.
					raise NodeError(
					  f"unknown target state {trans.target} for state {state.name} transition {trans.event}[{trans.guard}]",
					  trans.lineno) # ** Tested.

		# Verify for each state that if it has an initial transition, the transition targets a substate.
		for state in list(self.state_map.values()):
			if state.init:
				try:
					n = self.state_map[state.init.target]
				except KeyError as exc:
					raise NodeError(
					  f"initial transition for state {state.name} targeted an unknown state {state.init.target}",
					  state.init.lineno) from exc # ** Tested.
				while n:
					if n.name == state.name:
						break
					n = n.parent
				if n is None:
					raise NodeError(
					  f"initial transition for state {state.name} targeted a non-substate {state.init.target}",
					  state.init.lineno)  # ** Tested.

		# Add an initial transition if possible, else abort.
		if not self.init:
			if len(self.state) == 1:
				self.init = Init(self, self, {'target': self.state[0].name}, self.lineno)
			elif len(self.state) > 1:
				raise NodeError(f"machine {self.name} has no initial transition specified on reset", self.lineno)   # ** Tested.
		else: # Check that it exists.
			try:
				n = self.root.state_map[self.init.target]
			except KeyError as exc:
				raise NodeError(
				  f"initial transition for machine {self.name} targeted an unknown state {self.init.target}",
				  self.init.lineno) from exc 	# ** Tested.

def parse(xml_data):
	"Parse a state machine description and return a model."
	parser = XmlSerialiser(Machine)
	parser.parse(xml_data)
	return parser.current

# pylint: disable=unused-import,consider-using-with,unspecified-encoding
if __name__ == '__main__':
	import pprint
	print(parse(open(sys.argv[1], 'rt').read()))
