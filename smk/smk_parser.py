import xml.parsers.expat
import sys, re
from pprint import pprint
import smk_utils

# Generic Stuff
class NodeError(Exception):
    """Exception raised by Node subclasses when they cannot initialise themselves from attributes supplied.
        The lineno is supplied by the parser when it catches a NodeError exception and is then rethrown. """
    def __init__(self, msg, lineno=0):
        Exception.__init__(self, msg)
        self.msg, self.lineno = msg, lineno

class Node:
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
        self._lineno = lineno         
        if self.CONTENT[0]:
            setattr(self, self.CONTENT[0], self.CONTENT[1](''))
        self.characters = []
        self.simple_attribute = None
        self._add_attributes(attr)
        self._check_extra_attributes(attr)
        self._add_child_element_defaults()
        self._process_child_element_map()
    def _check_extra_attributes(self, attr):
        for k in attr:
            if k not in self.ATTRIBUTES:
                raise NodeError("extra attribute `%s` for element `%s`" % (k, self.klass())) # ** Tested
    def _add_attributes(self, attr):
        for k, v in list(self.ATTRIBUTES.items()):
            flags, validator = v
            if k not in attr:
                if flags == Node.OPT_MANDATORY:
                    raise NodeError("missing attribute `%s` for element `%s`" % (k, self.klass())) # ** Tested
                else:
                    setattr(self, k, validator(''))
            else:
                try:
                    setattr(self, k, validator(attr[k]))
                except Exception:
                    raise NodeError("bad attribute value %s='%s' for element `%s`" % (k, attr[k], self.klass())) # ** Tested
    def _add_child_element_defaults(self):
        for k, v in list(self.CHILD_ELEMENTS.items()):
            flags, validator = v
            if flags in (Node.OPT_MANDATORY, Node.OPT_OPTIONAL):
                setattr(self, k, None) # We use the presence of the None value to verify that this child is present.
            elif flags == Node.OPT_MULTI:
                setattr(self, k, [])
    def _process_child_element_map(self):
        for k in self.CHILD_ELEMENTS:
            validator_func = self.CHILD_ELEMENTS[k][1]
            if isinstance(validator_func, str):
                self.CHILD_ELEMENTS[k] = self.CHILD_ELEMENTS[k][0], eval(validator_func)
    @classmethod
    def klass(cls):
        return cls.__name__.lower()
    #def __nonzero__(self): return True
    def process_character_data(self, content):
        self.characters.append(content)
    def element_begin(self, name, attrs, lineno):
        if self.simple_attribute:
            NodeError("element `%s` cannot be nested within element `%s`" % (name, self.simple_attribute))  # ** Tested.
        try:
            flags, validator = self.CHILD_ELEMENTS[name]
        except KeyError:
            raise NodeError('element `%s` cannot be nested within element `%s`' % (name, self.klass())) # ** Tested
            
        # Now decide if we have a subclass (not an _instance_) of Node. Is there a better way to do this?
        try: is_complex_element = issubclass(validator, Node)
        except TypeError: is_complex_element = False
        if is_complex_element: 
            new_child = validator(self.root, self, attrs, lineno) # This element's parent is self.
            if flags in (Node.OPT_MANDATORY, Node.OPT_OPTIONAL):
                if getattr(self, name):
                    raise NodeError("element `%s` may not appear more than once as a child of `%s`" % 
                      (name, self.klass())) # ** Tested.
                else:
                    setattr(self, name, new_child)
            elif flags == Node.OPT_MULTI:
                getattr(self, name).append(new_child)
            return new_child
        else:
            self.simple_attribute = name
            return None
    def element_end(self, name):
        if self.simple_attribute:
            if self.simple_attribute != name:
                raise NodeError("internal error: close simple element: expected `%s`, got `%s`" % 
                  (self.simple_attribute, name)) # Not tested.
            flags, validator = self.CHILD_ELEMENTS[name]
            validated_value = validator(self.get_character_data())
            if flags in (Node.OPT_MANDATORY, Node.OPT_OPTIONAL):
                if getattr(self, name):
                    raise NodeError("element `%s` may not appear more than once as a child of `%s`" % 
                      (name, self.parent.klass()))
                else:
                    setattr(self, self.simple_attribute, validated_value)
            else:
                getattr(self, name).append(validated_value)            
            self.simple_attribute = None
            return False
        elif name != self.klass():
            raise NodeError("internal error: close element for <%s> _really_unexpected, expected `%s`, got `%s`" % 
                (self.klass(), name))  # Not tested.
        else: # We must have a subclass of Node...
            self._check_mandatory_present(self.CHILD_ELEMENTS)
            content = self.get_character_data().strip()
            if self.CONTENT[0]:     # If this element can have content...
                try:
                    setattr(self, self.CONTENT[0], self.CONTENT[1](content))
                except Exception as exc:
                    raise NodeError('content error %s for element `%s`' % (exc, self.klass())) # Not tested.
            else:   # Content illegal.
                if content:
                    raise NodeError('content illegal for element `%s`' % self.klass()) # ** Tested
            self.validate()
            return True
    def validate(self):
        "Check that the object is internally consistent after building."
        pass
    def _check_mandatory_present(self, attr_dict):
        for k in [k for (k, v) in list(attr_dict.items()) if v[0] == Node.OPT_MANDATORY]:
            try:
                getattr(self, k)
            except AttributeError:
                raise NodeError("mandatory attribute %s was not present") # ** Not Tested. 
    def get_character_data(self):
        char_data = ''.join(self.characters)
        self.characters = []
        return char_data
    def __str__(self):        
        strs = []
        self._dump(strs)
        return '\n'.join(strs)
    def _dump(self, strs, depth=1):
        strs.append('  ' * (depth-1) + '<<%s>>' % self.klass())
        all_attrs = [k for k in list(self.ATTRIBUTES.keys()) + [self.CONTENT[0]] + list(self.CHILD_ELEMENTS.keys()) if k]
        for k, val in [(k, getattr(self, k)) for k in all_attrs]:
            if isinstance(val, list):   
                if val and isinstance(val[0], Node):
                    for v in val:
                        v._dump(strs, depth+1)
                else:
                    strs.append('  ' * depth + '%s = `%s`' % (k, val))
            else:
                if isinstance(val, Node):
                    val._dump(strs, depth+1)
                else:
                    strs.append('  ' * depth + '%s = `%s`' % (k, val))
    __repr__ = __str__
    def _toxml(self, ostream, depth=1):
        indent = '  ' * (depth-1)
        ostream.write(indent + '<%s' % self.klass())
        
        # Emit attributes.
        for k in self.ATTRIBUTES:
            v = getattr(self, k)
            assert isinstance(v, str) # ATTRIBUTES are always strings.
            ostream.write(" %s='%s'" % (k, v))
            
        # If this node has no child elements and no content, close the tag now.
        if not self.CHILD_ELEMENTS and not self.CONTENT[0]:  
            ostream.write('/>\n')
        
        else:  # We know that it has either content or child elements.
            ostream.write('>')

            if self.CONTENT[0]:     # Emit content.
                v = getattr(self, self.CONTENT[0])
                if isinstance(v, str):
                    ostream.write(v)
                else:
                    ostream.write(' '.join(v)) # Assume some sort of sequence.
                
            # Emit attributes.
            if self.CHILD_ELEMENTS: # New line for child elements.
                ostream.write('\n')
                for k in self.CHILD_ELEMENTS:
                    v = getattr(self, k)
                    if v is None:
                        ostream.write(indent + '  <%s/>\n' % k)
                    elif isinstance(v, str):
                        ostream.write(indent + '  <%s>%s</%s>\n' % (k, v, k))
                    elif isinstance(v, Node):
                        v._toxml(ostream, depth+1)
                    elif isinstance(v, list):
                        for n in v:
                            n._toxml(ostream, depth+1)
                    else:
                        ostream.write(indent + '  <%s>%s</%s>\n' % (k, ' '.join(v), k)) # Assume some sort of sequence.
                        
                ostream.write(indent + '</%s>\n' % self.klass())
            else:
                ostream.write('</%s>\n' % self.klass())

class XmlSerialiser:
    """A cheesy little xml serialiser/deserialiser."""
    def __init__(self, root_type):
        self.xml_parser = xml.parsers.expat.ParserCreate()
        self.xml_parser.StartElementHandler = self.start_element
        self.xml_parser.EndElementHandler = self.end_element
        self.xml_parser.CharacterDataHandler = self.process_character_data
        self.current = None
        self.root_type = root_type
    def start_element(self, name, attrs):
        str_attrs = dict([(str(k), str(v)) for(k, v) in list(attrs.items())])
        str_name = str(name)
        if self.current is None:
            if self.root_type.klass() == str_name:
                self.current = self.root_type(None, None, str_attrs, self.xml_parser.CurrentLineNumber) 
                self.current.root = self.current
            else:
                raise NodeError("unknown root element: `%s`" % str_name) # ** Tested
        else:
            new_child = self.current.element_begin(str(str_name), str_attrs, self.xml_parser.CurrentLineNumber)
            if new_child:
                self.current = new_child
    def end_element(self, name):
        str_name = str(name)
        t = self.current.element_end(str_name)
        if t and self.current.parent:
            self.current = self.current.parent
    def process_character_data(self, content):
        self.current.process_character_data(str(content))
    def parse(self, s):
        try:
            self.xml_parser.Parse(s, 1)
        except xml.parsers.expat.ExpatError as exc: # XML parse error.
            raise NodeError('XML: ' + str(exc))
        except NodeError as exc: # Syntax error...
            if not exc.lineno:  # If lineno not given then fill in from the parser.
                exc.lineno = self.xml_parser.CurrentLineNumber 
            raise exc                               # ** Tested

# SMK Parser Stuff.
def mk_set(text):
    return smk_utils.OrderedSet(text.split())
def validate_name(n):
    n = n.strip()
    if not re.match(r'\w+$', n):
        raise ValueError("name `%s` illegal" % n) # ** Tested
    return n    
class Init(Node):
    CONTENT = ('action', lambda n: n.strip())
    ATTRIBUTES = {'target': (Node.OPT_MANDATORY, validate_name)}
    def __init__(self, *args): 
        Node.__init__(self, *args)
class Entry(Node):
    CONTENT = ('action', lambda n: n.strip())
    def __init__(self, *args): 
        Node.__init__(self, *args)
class Exit(Entry):
    def __init__(self, *args): 
        Entry.__init__(self, *args)

def validate_names(n):
    ns = n.split()
    for nn in n.split():
        if not re.match(r'\w+$', nn):
            raise ValueError("name `%s` illegal" % n) 
    return ns    
class Transition(Node):
    CONTENT = ('action', lambda n: n.strip())
    ATTRIBUTES = {
      'event': (Node.OPT_MANDATORY, validate_names),
      'target': (Node.OPT_OPTIONAL, lambda n: n.strip()),
      'guard': (Node.OPT_OPTIONAL, lambda n: n.strip()),
    }
    def __init__(self, *args): 
        Node.__init__(self, *args)
    def validate(self):
        for nn in self.event:
            self.root.event_list.add(nn)    # Add each event to set in machine.
        #self.root.event_list.add(self.event) 
        # We could check for an internal transition with no action, but this is valid as it allows a substate to ignore
        #  events that *are* handled by a superstate.
        # if not self.target and not self.action:
        #     raise NodeError("Degenerate transition %s does nothing", self)

class NodeWithInitTransition(Node):
    def __init__(self, *args): 
        Node.__init__(self, *args)
    def get_superstates(self):
        s = [self]
        while s[-1].parent:
            s.append(s[-1].parent)
        return s
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
        Node.__init__(self, *args)

        # Add to the root's state map, which is the primary data structure.
        if self.name in self.root.state_map:
            raise NodeError("duplicate state name %s" % self.name) # ** Tested.
        self.root.state_map[self.name] = self
    def validate(self):
        # Verify that all transition have distinct event signatures.
        # Also verifies that at most one transition for each event has no guard.
        trans = smk_utils.OrderedSet()
        for t in self.transition:
            trans_sig = (t.event, t.guard)
            if trans_sig in trans:
                raise NodeError("transition with signature %s[%s] duplicated" % (t.event, t.guard)) # ** Tested.
            else:
                trans.add(trans_sig)
		
        # Verify that initial transition does not target self.
        if self.init and self.init.target == self.name:
            raise NodeError("initial transition cannot target self") # ** Tested.

        # Verify that history & init are not both present.
#        if self.init and self.history:        
#            raise NodeError("cannot have an initial transition and a history in the same state %s" % self.name)

class Machine(NodeWithInitTransition): 
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
    def __init__(self, root, parent, attrs, lineno):
        Node.__init__(self, None, None, attrs, lineno)
        
        # We build a list in the machine of all states as we parse the input, allows us to detect duplicated states.
        self.state_map = {}

        # And a set of events.
        self.event_list = smk_utils.OrderedSet()
    def validate(self):
        # Verify target state for all transitions. 
        for state in list(self.state_map.values()):
            for trans in state.transition:
                if trans.target and trans.target not in self.state_map:        # Internal transitions have a nil target.
                    raise NodeError("unknown target state %s for state %s transition %s[%s]" % 
                      (trans.target, state.name, trans.event, trans.guard), trans._lineno) # ** Tested.

		# Verify for each state that if it has an initial transition, the transition targets a substate.
        for state in list(self.state_map.values()):
            if state.init:
                try: 
                    n = self.state_map[state.init.target]
                except KeyError: 
                    raise NodeError("initial transition for state %s targeted an unknown state %s" % 
                      (state.name, state.init.target), state.init._lineno)  # ** Tested.
                while n:
                    if n.name == state.name:
                        break
                    n = n.parent
                if n is None:
                    raise NodeError("initial transition for state %s targeted a non-substate %s" % 
                      (state.name, state.init.target), state.init._lineno)  # ** Tested.

        # Add an initial transition if possible, else abort.
        if not self.init:
            if len(self.state) == 1:
                self.init = Init(self, self, {'target': self.state[0].name}, self._lineno)
            elif len(self.state) > 1:
                raise NodeError("machine %s has no initial transition specified on reset" % 
                  self.name, self._lineno)   # ** Tested.
        else: # Check that it exists.
            try: 
                n = self.root.state_map[self.init.target]
            except KeyError: 
                raise NodeError("initial transition for machine %s targeted an unknown state %s" % 
                  (self.name, self.init.target), self.init._lineno)  # ** Tested.
    
def parse(s):
    p = XmlSerialiser(Machine)
    p.parse(s)
    return p.current
            
if __name__ == '__main__':           
    import pprint
    print(parse(open(sys.argv[1], 'rt').read()))


