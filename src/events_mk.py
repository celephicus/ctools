#! /usr/bin/python3

"""Code generator for events declarations."""

import os, sys, argparse, re
import codegen

DEFAULT_SRC_FILE = 'event.local.src'

TEMPLATE_FILE = '''\
# Event system event definition file.
# Format is:
#  <name> [<group>] "<description>"
#   <name> is a C identifier, usually all caps, will have "EV_" prepended and used in an enum.
#   <group> is a C identifier used to identify a group of events for a predefined trace mask. There may be multiple groups.
#   <description" is a short sentence.

SAMPLE_1	[default]			Frobs the foo.
SAMPLE_2	[default debug]		Frobs the foo some more.
'''

arg_parser = argparse.ArgumentParser(
	description="Build set of event definitions from a number of definition files."
)
arg_parser.add_argument('infile', help='input files', default=[DEFAULT_SRC_FILE], nargs='*')
arg_parser.add_argument('--output', '-o', help="output file, default input file with extension '.h'", dest='output_fn')
arg_parser.add_argument('--write-template', help='write example input file', action='store_true', dest='write_template')
def __define_symbol(symbol_def):
	try:
		symbol, value = symbol_def.split('=', 1)
		return symbol, value
	except ValueError as exc:
		raise argparse.ArgumentTypeError(f"'{symbol_def}' expected value like 'foo=bar'") from exc
arg_parser.add_argument('-D', type=__define_symbol, help='define a symbol', dest='defines', default=[], nargs='*')

codegen.Verbosity.add_argparse_options(arg_parser)
options = arg_parser.parse_args()
codegen.Verbosity.parse_options(options)	# Sort out verbosity.

# Default output filename if not given.
if not options.output_fn:
	options.output_fn = os.path.splitext(options.infile[0])[0]+'.h'

options.defines = dict(options.defines)

codegen.message(f"Command line options {options}\n", codegen.Verbosity.DEBUG)

# If we want a template file...
if options.write_template:
	template_fn = options.infile[0]
	codegen.message(f"Writing template file {template_fn} ... ")
	if os.path.isfile(template_fn):
		codegen.error('file exists, aborting')
	with open(template_fn, 'wt', encoding='utf-8') as f_template:
		try:
			f_template.write(TEMPLATE_FILE.format(guard=codegen.include_guard(template_fn)))
		except EnvironmentError:
			codegen.error("failed to write.")
	codegen.message("done.\n")
	sys.exit()

def read_logical_lines(fd):
	"""Open a file and read lines, ignoring blank lines and line comments. Lines with leading whitespace are joined
	to the previous line."""
	lns = []
	for lineno, ln in enumerate(fd, 1):	# pylint: disable=redefined-outer-name
		if not ln or ln.isspace() or ln.startswith('#'): continue		# Ignore blank & comments.
		join = ln[0].isspace()
		ln = re.sub(r'\s+', ' ', ln).strip()		# Munge whitespace to single space and strip leading & trailing.
		if join:		# If a continuation line...
			if not lns:
				codegen.error(f"continuation line at line {lineno} with no start") # Continuation with nothing to continue.
			lns[-1][1] = lns[-1][1] + ' ' + ln		# Add to previous.
		else:
			lns.append([(fd.name, lineno), ln])
	return lns

events = {}		# Our set of events live in a dict. Insertion order gives integer ID.
groups = {}		# Set of groups.
multi = {}		# Record multi events so that we can emit a count.

# Process input files.
cg = codegen.Codegen(options.infile, options.output_fn)

for ll in sum(cg.begin(reader=read_logical_lines), []):
	loc = f'{ll[0][0]}:{ll[0][1]}' # String <file>:<lineno> for error messages.

	ln = ll[1]			# Substitute in symbols.
	for sym, repl in options.defines.items():
		ln = re.sub(r'\$'+sym, repl, ln)

	try:
		ev_name, ev_multi, raw_groups, ev_desc = re.match(r'''
		  (.*?) (?:\[(.*?)\])? \s+				# <ident> or <ident>[<number>]
		  (?:\[(.*)\])* \s*
		  (.*)$''',
		  ln, re.I|re.X).groups()
	except AttributeError:
		codegen.error(f"failed to parse definition at {loc}")
	ev_groups = [] if not raw_groups else raw_groups.lower().split()
	ev_groups.append('all')

	def __add_event(e_n, e_gps, e_desc):
		" Add a single event to the collection."
		if e_n in events:
			codegen.error(f"event {e_n} at {loc} already exists.") 	#pylint: disable=cell-var-from-loop
		for x in e_gps:
			if x not in groups:
				groups[x] = 0
		events[e_n] = e_gps, e_desc

	if not ev_multi:
		__add_event(ev_name, ev_groups, ev_desc)
	else:
		try:
			nn = int(ev_multi)
		except ValueError:
			codegen.error(f"multi definition must be an integer count at {loc}")
		if nn > 0:
			multi[ev_name] = nn
			for n in range(nn):
				__add_event(ev_name+str(n), ev_groups, ev_desc if n == 0 else "")

# Compute size of mask. Since we access this as 16 bit words, round up size.
MASK_SIZE = 2 * ((len(events)+15)//16)

# Compute trace masks.
for ev_g in [x[0] for x in reversed(events.values())]:
	for g in groups:
		groups[g] <<= 1
		if g in ev_g:
			groups[g] |= 1

# We have enough to generate the event definitions.
cg.add_autogen_comment()
cg.add_include_guard()

# Event ID enum.
cg.add_comment('Event IDs')
cg.add('enum {', indent=+1)
for n, ev in enumerate(events.items()):
	cg.add(f'EV_{ev[0]} = {n},', trailer=f'// {ev[1][1]}', col_width=40)
cg.add(f'COUNT_EV = {len(events)},', trailer='// Total number of events defined.', col_width=40)
cg.add('};', indent=-1, add_nl=1)

# Counts for multi events.
cg.add_comment('Multi event counts.')
for ev_name, count in multi.items():
	cg.add(f"#define EVENT_COUNT_{ev_name.rstrip('_')} {count}")
cg.add_nl()

# We have a bitmask to decide what events to trace.
cg.add_comment('Size of trace mask in bytes.')
cg.add(f'#define EVENT_TRACE_MASK_SIZE {MASK_SIZE}', add_nl=+1)

# Generate some tracemasks.
for g,v in groups.items():
	cg.add_comment(f'Trace mask {g}.')
	cg.add(
	  f"#define EVENT_DECLARE_TRACE_MASK_{g.upper()}() static const uint8_t TRACE_MASK_{g.upper()}[] PROGMEM = {{",
	  indent=1, trailer='\\', col_width=100)
	cg.add(', '.join([f"0x{(v >> n) & 0xff:02x}" for n in range(0, len(events), 8)]), trailer='\\', col_width=100)
	cg.add("}", indent=-1, add_nl=1)

# Event names as strings.
cg.add_comment('Event Names.')
cg.add_avr_array_strings('EVENT_NAMES', events.keys(), lead_str='EVENT_DECLARE')
cg.add_nl()

# Event descriptions as strings.
cg.add_comment('Event Descriptions.')
cg.add_avr_array_strings('EVENT_DESCS', [x[1] for x in events.values()], col=140, lead_str='EVENT_DECLARE')
cg.add_nl()

# Finalise output file.
cg.end()
