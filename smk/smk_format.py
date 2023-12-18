"""Output formatting classes for smk."""

import sys, re, os, io, copy, textwrap, pprint
import smk_utils

# This warning flagged for Formatter subclasses that inherit member attributes.
# pylint: disable=no-member

def splitcode(code):
	"""Given a string or list of strings representing "C" expressions, return a list of expressions."""
	if not code:
		return []
	if isinstance(code, str):
		code = [code]
	exprs = []
	for frag in code:
		exprs += [x for x in [x.strip() for x in frag.split(';')] if x]
	return exprs

# I like wide code.
COLUMNS = 120
def pretty_fill(text):
	"Formats a string so that the max width is COLUMNS."
	return textwrap.fill(text, width=COLUMNS)

class OutputFormatter:
	"""Abstract base class for a class that takes a model and generates one or more output files. It takes care not to
		touch the file(s) if the new contents are identical. It deletes the file(s) on error."""
	# List of default filenames, also defines number of output files and their extensions.
	DEFAULT_FILENAMES = ('output.txt',)
	STREAMS = ('DEFAULT',)

	# Define various macros that the formatter uses. These can be overridden if required.
	SYMBOL_DEFINITIONS = {}

	RE_SYMBOL = re.compile(r'\$\(([a-z_]+)\)', re.I)
	@staticmethod
	def sub(text, symbols):
		"Perform macro substitution from dict symbols into s, where macros are called as $(foo)."
		def subber(m):
			sol = text.rfind('\n', 0, m.start())
			indent = text[sol+1:m.start()]
			if indent and not indent.isspace():
				indent = ''
			repl = symbols[m.group(1)].splitlines()
			if not repl:
				return ''
			indented_repl = '\n'.join([repl[0]] + [indent + x for x in repl[1:]])
			return indented_repl
		while 1:
			text, in_progress = OutputFormatter.RE_SYMBOL.subn(subber, text)
			if not in_progress:
				return text

	def __init__(self, path, options, extra_symbol_defs=None):
		"""Initialise with a path. If the Formatter has more than 1 output file, the supplied extension (if any) is
			removed and the extensions from the DEFAULT_FILENAMES member are used instead."""
		self.options = options
		self.filepaths = self._get_filepaths(path)
		self.ofs = []
		assert len(self.filepaths) == len(self.STREAMS)
		for i, ostream in enumerate(self.STREAMS):
			setattr(self, ostream, i)
			self.ofs.append(io.StringIO())

		# Build a dict of symbol definitions that we use.
		self.symbol_definitions = copy.deepcopy(self.SYMBOL_DEFINITIONS)
		self.symbol_definitions.update(extra_symbol_defs or {})

		# Build a dict of symbols with default values.
		self.symbols = {n: v[0] for n, v in self.symbol_definitions.items()}

	def _get_filepaths(self, path):
		"Return a list of output file paths."
		if not path: # Give a default filename.
			return self.DEFAULT_FILENAMES
		if len(self.DEFAULT_FILENAMES) > 1 or not os.path.splitext(path)[1]: # Frob the extensions.
			return tuple([os.path.splitext(path)[0] + os.path.splitext(p)[1] for p in self.DEFAULT_FILENAMES]) # pylint: disable=consider-using-generator
		return (path,)

	def blurt(self, msg):
		"Write a message depending on verbosity setting."
		if self.options.verbosity:
			sys.stdout.write(msg + '\n')

	def _preprocess(self, text):
		pass

	def write(self, text, stream=0):
		"Write data to specified stream."
		self.ofs[stream].write(self._preprocess(OutputFormatter.sub(text, self.symbols)))

	def close(self):
		"Finished writing so write all streams to output files"
		for filepath, ostream in zip(self.filepaths, self.ofs):
			outstr = ostream.getvalue()
			ostream.close()

			try:		# Read existing file contents, if any.
				with open(filepath, 'rt', encoding="utf-8") as fout_r:
					existing = fout_r.read()
			except EnvironmentError:
				existing = None

			if existing != outstr:	# Write if changed.
				with open(filepath, 'wt', encoding="utf-8") as fd_out:
					fd_out.write(outstr)
				self.blurt(f"Wrote file `{filepath}'.")
			else:
				self.blurt(f"File `{filepath}' not written as unchanged.")

	def abort(self):
		"Something has gone wrong. Attempt to delete all output files."
		for filepath in self.filepaths:
			if os.path.exists(filepath):
				try:
					os.remove(filepath)
					self.blurt(f"Deleted file `{filepath}'.")
				except OSError:
					self.blurt(f"Failed to delete file `{filepath}'.")

	def generate(self, model):
		"Override in subclasses to write output."
		raise NotImplementedError

class Formatter_XML(OutputFormatter): 	# pylint: disable=invalid-name
	"Emit model as nicely formatted XML. Still XML though."
	DEFAULT_FILENAMES = ('output.xml',)
	STREAMS = ('DEFAULT',)
	def generate(self, model):
		"Generate output."
		model['.machine'].toxml(self.ofs[self.DEFAULT])

class Formatter_C(OutputFormatter):		# pylint: disable=invalid-name
	"Emit C code with an external context variable."
	SYMBOL_DEFINITIONS = {
		'EVENT_ACCESSOR': (
		  '(ev)',
		  '''The code fragment used to access the event ID in the body of the process() function from the event instance.
			 The event is in variable 'ev'.'''
		),
		'EVENT_REFERENCE_TYPE': (
		  't_event',
		  '''The code fragment used to reference the event type, as used in function definitions'''
		),
		'STATE_NAME_PREFIX': (
		  'ST_$(MACHINE_NAME_UC)_',
		  '''Macro used to form explicit state names in the source files.'''
		),
		'STATE_TYPE': (
		  'uint8_t',
		  '''Type used to hold the state variable. Should be an efficient integer type, usually uint8_t or int.'''
		),
		'RESET_EVENT_NAME': (
		  'EV_SM_RESET',
		  '''Name of the reset event that resets the machine to it's intial state.'''
		),
		'CHANGE_STATE_HOOK': (
		  '',
		  '''Macro that takes a single parameter that is the integer state ID, called whenever the state machine
				changes state. Typically used for logging.'''
		),
	}
	EXTRA_SYMBOL_DEFINITIONS = {}
	DEFAULT_FILENAMES = ('output.h', 'output.cpp')
	STREAMS = ('HEADER', 'SOURCE')
	def __init__(self, path, options, extra_symbol_defs=None):
		OutputFormatter.__init__(self, path, options, extra_symbol_defs or self.EXTRA_SYMBOL_DEFINITIONS)

	@staticmethod
	def assert_transition_map_is_valid(transmap):
		"""Transmap is a list of (guard, [actions], target). To generate valid code we assert that the first N-1
			items in the list have guards (the last item can have a guard or not, we don't care."""
		for guard in [x[0] for x in transmap[:-1]]:
			assert guard, f"Unguarded transition found in first N-1 items of {pprint.pformat(transmap, width=120)}"

	@staticmethod
	def mk_event_name(ev_name):
		"Make a canonical event name."
		return ev_name.upper()

	RE_PREPROCESS = re.compile(r'\$SMK_CHANGE_STATE\((\w+)\)')
	def _preprocess(self, text):
		repl = '; '.join([x for x in (self.symbols['CHANGE_STATE_HOOK'], 'PROP(state_) = st_') if x and not x.isspace()])
		def subber(m):
			return repl.replace('st_', m.group(1))
		return self.RE_PREPROCESS.sub(subber, text)

	def _generate_is_in_state_data(self, model):
		""" We generate a matrix of bitmasks that are used to determine if the SM is in a particular state, which might
		be an abstract state with no transitions, only with entry.exit actions, used as a container for substates.
		"""
		pprint.pprint(model['.in_state'])
		superstate_map = model['.in_state']
		states = list(superstate_map.keys())
		STRIDE = (len(states) + 7) // 8 # Each entry is this bytes wide. # pylint: disable=invalid-name
		is_in_data = []
		for sm_state_name in superstate_map:
			mask = 0
			for check_state_name in superstate_map[sm_state_name]:
				mask |= 1 << states.index(check_state_name)
			is_in_data += [(mask >> (i*8)) & 0xff for i in range(STRIDE)]

		self.symbols['IS_IN_DATA'] = pretty_fill(', '.join([f'0x{x:02x}' for x in is_in_data]))
		self.symbols['IS_IN_DATA_DIM'] = str(STRIDE)

	def generate(self, model):	# pylint: disable=too-many-branches,too-many-statements,too-many-locals
		"Generate output."

		self.symbols['MACHINE_NAME'] = model['.machine'].name
		self.symbols['MACHINE_NAME_UC'] = model['.machine'].name.upper()
		self.symbols['HEADER_FILE_NAME'] = self.filepaths[self.HEADER]
		self.symbols['SOURCE_FILE_NAME'] = self.filepaths[self.SOURCE]

		# Process verbatim sections in machine declaration.
		for elementname, symbolname in (('include', 'VERBATIM_INCLUDE'), ('code', 'VERBATIM_CODE')):
			content = getattr(model['.machine'], elementname)
			if content:
				source_code = f"""\
/* Verbatim `{elementname}' code. */
{content}
/* Verbatim `{elementname}' code ends. */
"""
				self.symbols[symbolname] = source_code
			else:
				self.symbols[symbolname] = ''

		self.symbols['CONTEXT_DECL'] = \
		  '\n'.join([f'{x};' for x in ['$(STATE_TYPE) state_'] + splitcode(model['.machine'].property)])
		reset_actions, reset_state = model['.machine'].get_init_actions_state()
		self.symbols['STATE_DECL'] = \
		  ',\n'.join([f'{smk_utils.mk_state_name(x)} = {i}' for i, x in enumerate(model['.machine'].state_map)])
		reset_code = '\n'.join([f'    {x};' for x in splitcode(reset_actions)])
		self.symbols['RESET_FUNCTION_BODY'] = reset_code or '/* empty */'
		self.symbols['INITIAL_STATE'] = smk_utils.mk_state_name(reset_state.name)

		self._generate_is_in_state_data(model)

		# Write main nested switch statement body.
		handler = []
		for st_name, evdict in model.items():	# pylint: disable=too-many-nested-blocks
			#print(st_name, evdict)
			if st_name.startswith('.'):
				continue
			handler.append(f'case {smk_utils.mk_state_name(st_name)}:')
			handler.append('    switch($(EVENT_ACCESSOR)) {')

			for ev_name, event_defs in evdict.items():
				handler.append(f'    case {self.mk_event_name(ev_name)}:')

				# Check if the only action for this handler is a goto,
				if isinstance(event_defs, str):
					handler.append('        ' + event_defs)
				else:
					self.assert_transition_map_is_valid(event_defs)

					# Add label if this handler is targetted by a goto:
					try:
						label = model['.goto_labels'][st_name][ev_name]
						handler.append(label)
					except KeyError:
						pass

					for trans_index, (guard, actions, target) in enumerate(event_defs):	# pylint: disable=unused-variable
						if guard:
							if trans_index == 0:
								handler.append(f'    if({guard}) {{')
							else:
								handler.append(f'    else if({guard}) {{')
						else:
							if trans_index > 0:
								handler.append('    else {')

						# Emit all actions...
						for action in splitcode(actions):
							if not action.endswith(';'):
								action = action + ';'
							handler.append('        ' + action)

						if guard or trans_index > 0:
							handler.append('    }')

					handler.append('    break;')
			handler.append('}')
			handler.append('break;')
		self.symbols['HANDLER_BODY'] = '\n'.join(handler)

		self.write(self.HEADER_TEMPLATE, stream=self.HEADER)
		self.write(self.SOURCE_TEMPLATE, stream=self.SOURCE)

class Formatter_C_StaticContext(Formatter_C):	# pylint: disable=invalid-name
	"Emit code for a state machine with a static context variable, so only one instance can be used,"

	@staticmethod
	def insert_lines(txt1, txt2):
		"""Insert a bunch of lines from txt2 just before the last line in txt1.
		Used for munging templates to add stuff at the end."""
		lns1 = txt1.splitlines(True)
		lns2 = txt2.splitlines(True)
		return ''.join(lns1[:-1] + lns2 + lns1[-1:])

	HEADER_TEMPLATE = """\
/* This file is auto-generated. Do not edit. */

/* Pass an event to the machine. */
void smk_process_$(MACHINE_NAME)($(EVENT_REFERENCE_TYPE) ev);

/* State ID declaration. */
enum {
    $(STATE_DECL)
};

/* EOF */
"""
	SOURCE_TEMPLATE = """\
/* This file is auto-generated. Do not edit. */

$(VERBATIM_INCLUDE)

#include "$(HEADER_FILE_NAME)"

/* Context type declaration */
typedef struct {
    $(CONTEXT_DECL)
} smk_context_$(MACHINE_NAME)_t;

static smk_context_$(MACHINE_NAME)_t context;

#define PROP(member_) (context.member_)

$(VERBATIM_CODE)

void smk_process_$(MACHINE_NAME)($(EVENT_REFERENCE_TYPE) ev) {
    if ($(RESET_EVENT_NAME) == $(EVENT_ACCESSOR)) {
        $SMK_CHANGE_STATE($(INITIAL_STATE));
        $(RESET_FUNCTION_BODY)
        return;
    }

    switch(context.state_) {
    default:
        break;
    
    $(HANDLER_BODY)
    }
}

/* EOF */
"""
	def __init__(self, path, options):
		Formatter_C.__init__(self, path, options)


class Formatter_C_StaticContextIsIn(Formatter_C_StaticContext): 	# pylint: disable=invalid-name
	"Emit code for a function to check if we are in a particulat state or substate thereof."
	HEADER_TEMPLATE = Formatter_C_StaticContext.insert_lines(Formatter_C_StaticContext.HEADER_TEMPLATE, """\
bool smk_is_in_$(MACHINE_NAME)($(STATE_TYPE) state);

""")
	SOURCE_TEMPLATE = Formatter_C_StaticContext.insert_lines(Formatter_C_StaticContext.SOURCE_TEMPLATE, """\
static const uint8_t is_in_data[] = {
    $(IS_IN_DATA)
};

bool smk_is_in_$(MACHINE_NAME)($(STATE_TYPE) state) {
    return !!(is_in_data[(context.state_ * $(IS_IN_DATA_DIM)) + state/8] & (1 << state%8));
}

""")
