import sys, re, os, io, copy, textwrap, pprint
import smk_utils

def splitcode(s):
	"""Given a string or list of strings representing "C" expressions, return a list of expressions."""
	if not s:
		return []
	if isinstance(s, str):
		s = [s]
	exprs = []
	for ss in s:
		exprs += [x for x in [x.strip() for x in ss.split(';')] if x]
	return exprs

# I like wide code.
COLUMNS = 120
def pretty_fill(s, indent=0):
	return textwrap.fill(s, width=COLUMNS)

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
	def sub(s, symbols):
		"Perform macro substitution from dict symbols into s, where macros are called as $(foo)."
		def subber(m):
			sol = s.rfind('\n', 0, m.start())
			indent = s[sol+1:m.start()]
			if indent and not indent.isspace():
				indent = ''
			repl = symbols[m.group(1)].splitlines()
			if not repl:
				return ''
			else:
				indented_repl = '\n'.join([repl[0]] + ['%s%s' % (indent, x) for x in repl[1:]])
				return indented_repl
		while 1:
			s, n = OutputFormatter.RE_SYMBOL.subn(subber, s)
			if not n:
				return s

	def __init__(self, path, options, extra_symbol_defs=None):
		"""Initialise with a path. If the Formatter has more than 1 output file, the supplied extension (if any) is
			removed and the extensions from the DEFAULT_FILENAMES member are used instead."""
		self.options = options
		self.filepaths = self._get_filepaths(path)
		self.ofs = []
		assert len(self.filepaths) == len(self.STREAMS)
		for i, s in enumerate(self.STREAMS):
			setattr(self, s, i)
			self.ofs.append(io.StringIO())

		# Build a dict of symbol definitions that we use.
		self.symbol_definitions = copy.deepcopy(self.SYMBOL_DEFINITIONS)
		self.symbol_definitions.update(extra_symbol_defs or {})

		# Build a dict of symbols with default values.
		self.symbols = dict([(n, v[0]) for (n, v) in self.symbol_definitions.items()])

	def _get_filepaths(self, path):
		"Return a list of output file paths."
		if not path: # Give a default filename.
			return self.DEFAULT_FILENAMES
		if len(self.DEFAULT_FILENAMES) > 1 or not os.path.splitext(path)[1]: # Frob the extensions.
			return tuple([os.path.splitext(path)[0] + os.path.splitext(p)[1] for p in self.DEFAULT_FILENAMES])
		return (path,)
	def blurt(self, msg):
		if self.options.verbosity:
			sys.stdout.write(msg + '\n')
	def preprocess(self, s):
		pass
	def write(self, s, stream=0):
		self.ofs[stream].write(self.preprocess(OutputFormatter.sub(s, self.symbols)))
	def close(self):
		for filepath, of in zip(self.filepaths, self.ofs):
			outstr = of.getvalue()
			of.close()
			try:
				existing = open(filepath, 'rt').read()
			except Exception:
				existing = None
			if existing != outstr:
				open(filepath, 'wt').write(outstr)
				self.blurt('Wrote file `%s`.' % filepath)
			else:
				self.blurt('File `%s` not written as unchanged.' % filepath)
	def abort(self):
		for filepath in self.filepaths:
			if os.path.exists(filepath):
				try:
					os.remove(filepath)
					self.blurt('Deleted file `%s`.' % filepath)
				except OSError:
					self.blurt('Failed to delete file `%s`.' % filepath)
	def generate(self, model, nmgr, options):
		raise NotImplementedError

class Formatter_XML(OutputFormatter):
	DEFAULT_FILENAMES = ('output.xml',)
	STREAMS = ('DEFAULT',)
	def __init__(self, path, options, extra_symbol_defs=None):
		OutputFormatter.__init__(self, path, options, extra_symbol_defs)
	def generate(self, model):
		model['.machine']._toxml(self.ofs[self.DEFAULT])

class Formatter_C(OutputFormatter):
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
	def assert_transition_map_is_valid(self, transmap):
		"""Transmap is a list of (guard, [actions], target). To generate valid code we assert that the first N-1
			items in the list have guards (the last item can have a guard or not, we don't care."""
		for guard, actions, target in transmap[:-1]:
			assert guard, "Unguarded transition found in first N-1 items of %s." % pprint.pformat(transmap, width=120)
	def mk_event_name(self, ev_name):
		return ev_name.upper()

	RE_PREPROCESS = re.compile(r'\$SMK_CHANGE_STATE\((\w+)\)')
	def preprocess(self, s):
		repl = '; '.join([x for x in (self.symbols['CHANGE_STATE_HOOK'], 'PROP(state_) = st_') if x and not x.isspace()])
		def subber(m):
			return repl.replace('st_', m.group(1))
		return self.RE_PREPROCESS.sub(subber, s)

	def generate(self, model):
		self.symbols['MACHINE_NAME'] = model['.machine'].name
		self.symbols['MACHINE_NAME_UC'] = model['.machine'].name.upper()
		self.symbols['HEADER_FILE_NAME'] = self.filepaths[self.HEADER]
		self.symbols['SOURCE_FILE_NAME'] = self.filepaths[self.SOURCE]

		# Process verbatim sections in machine declaration.
		for elementname, symbolname in (('include', 'VERBATIM_INCLUDE'), ('code', 'VERBATIM_CODE')):
			content = getattr(model['.machine'], elementname)
			if content:
				#content = ''.join(['%s\n' % x for x in splitcode(content)])
				source_code = \
				  '/* Verbatim `%s` code. */\n%s/* Verbatim `%s` code ends. */\n' % (elementname, content, elementname)
				self.symbols[symbolname] = source_code
			else:
				self.symbols[symbolname] = ''

		self.symbols['CONTEXT_DECL'] = \
		  '\n'.join(['%s;' % x for x in ['$(STATE_TYPE) state_'] + splitcode(model['.machine'].property)])
		reset_actions, reset_state = model['.machine'].get_init_actions_state()
		self.symbols['STATE_DECL'] = \
		  ',\n'.join(['%s = %d' % (smk_utils.mk_state_name(x), i) for i, x in enumerate(model['.machine'].state_map)])
		reset_code = '\n'.join(['    %s;' % x for x in splitcode(reset_actions)]);
		self.symbols['RESET_FUNCTION_BODY'] = reset_code or '/* empty */'
		self.symbols['INITIAL_STATE'] = smk_utils.mk_state_name(reset_state.name)

		# Generate data for in_state() function.
		is_in_data = []
		for state_name, is_in_array in model['.in_state'].items():
			array_len = ((len(is_in_array) + 7) // 8)
			is_in_array += [False] * (array_len * 8 - len(is_in_array)) # Pad to multiple of 8.
			for i in range(array_len):
				d = 0
				for j in range(8):
					d = (d >> 1) | (is_in_array.pop(0) * 0x80)
				is_in_data.append(d)

		self.symbols['IS_IN_DATA'] = pretty_fill(', '.join(['0x%02x' % x for x in is_in_data]))
		self.symbols['IS_IN_DATA_DIM'] = str(array_len)

		# Write main nested switch statement body.
		handler = []
		for st_name, evdict in model.items():
			#print(st_name, evdict)
			if st_name.startswith('.'):
				continue
			handler.append('case %s:' % smk_utils.mk_state_name(st_name))
			handler.append('    switch($(EVENT_ACCESSOR)) {')

			for ev_name, event_defs in evdict.items():
				handler.append('    case %s:' % self.mk_event_name(ev_name))

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

					for trans_index, trans_def in enumerate(event_defs):
						guard, actions, target = trans_def
						if guard:
							if trans_index == 0:
								handler.append('    if(%s) {' % guard)
							else:
								handler.append('    else if(%s) {' % guard)
						else:
							if trans_index > 0:
								handler.append('    else {')

						# Emit all actions...
						for a in splitcode(actions):
							if not a.endswith(';'):
								a = a + ';'
							handler.append('        ' + a)

						if guard or trans_index > 0:
							handler.append('    }')

					handler.append('    break;')
			handler.append('}')
			handler.append('break;')
		self.symbols['HANDLER_BODY'] = '\n'.join(handler)

		self.write(self.HEADER_TEMPLATE, stream=self.HEADER)
		self.write(self.SOURCE_TEMPLATE, stream=self.SOURCE)

class Formatter_C_StaticContext(Formatter_C):
	@staticmethod
	def insertLines(s1, s2):
		lns1 = s1.splitlines(1)
		lns2 = s2.splitlines(1)
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


class Formatter_C_StaticContextIsIn(Formatter_C_StaticContext):
	HEADER_TEMPLATE = Formatter_C_StaticContext.insertLines(Formatter_C_StaticContext.HEADER_TEMPLATE, """\
bool smk_is_in_$(MACHINE_NAME)($(STATE_TYPE) state);

""")
	SOURCE_TEMPLATE = Formatter_C_StaticContext.insertLines(Formatter_C_StaticContext.SOURCE_TEMPLATE, """\
static const uint8_t is_in_data[] = {
    $(IS_IN_DATA)
};

bool smk_is_in_$(MACHINE_NAME)($(STATE_TYPE) state) {
    return !!(is_in_data[(context.state_ * $(IS_IN_DATA_DIM)) + state/8] & (1 << state%8));
}

""")
	def __init__(self, path, options):
		Formatter_C_StaticContext.__init__(self, path, options)

