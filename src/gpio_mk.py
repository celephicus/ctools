#! /usr/bin/python3

"""Code generator to turn a CSV representation of GPIO signals into a bunch of definitions for a C header file.
"""
import re, os, argparse
import csv_parser
import codegen

INFILE_DEFAULT = 'gpio.csv'

# Parse command line arguments.
arg_parser = argparse.ArgumentParser(
	description='Code generator to turn a CSV representation of GPIO signals into definitions in a C header file.')
arg_parser.add_argument('infile', default=INFILE_DEFAULT, help='Input csv file.')
arg_parser.add_argument('--output', '-o', default=None, help="output file, default input file with extension '.h'")

codegen.Verbosity.add_argparse_options(arg_parser)
options = arg_parser.parse_args()
codegen.Verbosity.parse_options(options)	# Sort out verbosity.
if not options.output:
	options.output = os.path.splitext(os.path.basename(options.infile))[0] + '.h'	# Write to current directory

class GPIOParse(csv_parser.CSVparse):
	"""Class to handle parsing a CSV file with GPIO definitions.

	pin    sig       func desc     group     apin  ppin port note
	D1/TXD,RS485_TXD,TXD0,RS485 TX,RS485 Bus,J7/12,31,  PD1, TXD/PCINT17,Bootloader
	"""
	def __init__(self):
		csv_parser.CSVparse.__init__(self)
		self.COLUMN_NAMES = 'Pin Sig Func Description Group Apin Ppin Port AltFunc Comment'.split() # pylint: disable=invalid-name
		self.metadata = { 'symbol': {}}

	# Directives...
	def handle_directive_processor(self, directive, data):
		"""Processor has args family, type; e.g AVR8, Arduino Pro Micro 3.3V/8MHz.
			Family must match a known family, type is free-form."""
		if directive in self.metadata:
			self.error(f"directive `{directive}' can only appear once")
		p_family, p_type = data[:2]
		self.metadata[directive] = p_family.lower(), p_type		# We check this later.
	def handle_directive_project(self, directive, data):
		"Project is free form."
		if directive in self.metadata:
			self.error(f"directive `{directive}' can only appear once")
		self.metadata[directive] = data[0]
	def handle_directive_symbol(self, directive, data):	 # pylint: disable=unused-argument
		"Args macro, value, comment, e.g @symbol,FOO,33,What to from the foo."
		macro, d_val, d_comment = data[:3]
		if not codegen.is_ident(macro):
			self.error(f"bad symbol name `{macro}'")
		self.metadata['symbol'][macro] = d_val, d_comment
	def on_first_data(self):
		"Validate that we have the correct metadata."
		p_family = self.metadata.get('processor', ['*none*'])[0]
		if p_family != 'avr8':
			self.error(f"cannot use processor `{p_family}'")

	# Data, these are mostly static methods as they do not need instance or class access.
	@staticmethod
	def validate_col_Pin(pin_name): # pylint: disable=invalid-name
		"Turn a pin name like D1/TXD -> '1'"
		pin_name = pin_name.split('/')[0] 				# Get rid of possible alternate pin name after slash.
		if pin_name.startswith('D'): 				# Arduino pins might start with a D
			pin_name = pin_name[1:]
		return pin_name
	@staticmethod
	def validate_col_Sig(signame): # pylint: disable=invalid-name
		'Must be a valid C identifier, return ALL_CAPS.'
		if signame:
			signame = codegen.ident_allcaps(signame)
		return signame
	@staticmethod
	def validate_col_Group(x): # pylint: disable=invalid-name
		"Set to explicit `None' rather than empty."
		return x or 'None'
	def validate_col_Port(self, port): # pylint: disable=invalid-name
		"""Expected either blank or port like `PA3'."""
		# If present then set extra keys to row io_port & io_bit.
		# TODO: Pattern should be configurable for diffferent processors.
		if port.startswith('P'):
			m = re.match(r'(?:(?:P([A-Z]))|(ADC))([0-7])$', port)	# Parse out port, bit from like `PA3'.
			self.add_extra('io_port', m.group(1) or m.group(2))
			self.add_extra('io_bit', int(m.group(3)))
		return port

# Parse...
cg = codegen.Codegen(options.infile, options.output)
parser = GPIOParse()
cg.begin(parser.read)

# Postprocess a bit...
pins = {}
direct = []
unused = []
for d in parser.data:
	# print(d)
	if 'unused' in d['Func']:							# An unused pins is just listed as unused with not further definitions.
		unused.append(d['Pin'])

	if not d['Sig']: continue							# Ignore pins with no signal name.

	if d['Group'] not in pins: pins[d['Group']] = []	# Ready to insert new group...
	pins[d['Group']].append((f"GPIO_PIN_{d['Sig']} = {d['Pin']}", d['Description']))		# Insert Arduino pin definition.

	if 'direct' in d['Func']:							# Insert a bunch of inline functions to directly access the pin.
		direct.append((d['Sig'], d['Description'], d['io_port'], d['io_bit']))

# Write output file...
cg.add_include_guard()
cg.add_autogen_comment()

proc_family_type = parser.metadata["processor"]
cg.add_comment(f'Pin Assignments for processor {proc_family_type[1]} [{proc_family_type[0]}], project: {parser.metadata.get("project", "<none>")}.')

cg.add('enum {')
cg.indent()
for group, pins in pins.items():
	cg.add_comment(group)
	for pindef in pins:
		cg.add(codegen.format_code_with_comments(pindef[0] + ',', pindef[1]))
	cg.add_nl()
cg.add('};', indent=-1, eat_nl=True)

if parser.metadata['symbol']:
	cg.add_comment("Extra symbols from symbol directive.", add_nl=-1)
	for sym, vc in parser.metadata['symbol'].items():
		val, comment = vc
		cg.add(f"#define GPIO_{sym} {val} // {comment}")
	cg.add_nl()

if direct:
	cg.add_comment('Direct access ports.', add_nl=-1)
	for sig, desc, io_port, io_bit in direct:
		cg.add_comment(f"{sig}: {desc}", add_nl=-1)
		sigCC = codegen.ident_camel(sig, leading=True)
		cg.add(codegen.mk_short_function(f"gpio{sigCC}SetModeOutput", f"DDR{io_port} |= _BV({io_bit});", leader='static inline'))
		cg.add(codegen.mk_short_function(f"gpio{sigCC}SetModeInput", f"DDR{io_port} &= ~_BV({io_bit});", leader='static inline'))
		cg.add(codegen.mk_short_function(f"gpio{sigCC}SetMode", f"if (fout) DDR{io_port} |= _BV({io_bit}); else DDR{io_port} &= ~_BV({io_bit});",
		  leader='static inline', args='bool fout'))
		cg.add(codegen.mk_short_function(f"gpio{sigCC}Read", f"return PIN{io_port} | _BV({io_bit});", ret='bool', leader='static inline'))
		cg.add(codegen.mk_short_function(f"gpio{sigCC}Toggle", f"PORT{io_port} ^= _BV({io_bit});", leader='static inline'))
		cg.add(codegen.mk_short_function(f"gpio{sigCC}Set", f"PORT{io_port} |= _BV({io_bit});", leader='static inline'))
		cg.add(codegen.mk_short_function(f"gpio{sigCC}Get", f"return PORT{io_port} & _BV({io_bit});", ret='bool', leader='static inline'))
		cg.add(codegen.mk_short_function(f"gpio{sigCC}Clear", f"PORT{io_port} &= ~_BV({io_bit});", leader='static inline'))
		cg.add(codegen.mk_short_function(f"gpio{sigCC}Write", f"if (b) PORT{io_port} |= _BV({io_bit}); else PORT{io_port} &= ~_BV({io_bit});",
		  leader='static inline', args='bool b'))

if unused:
	cg.add_comment("List unused pins", add_nl=-1)
	cg.add(f"#define GPIO_UNUSED_PINS {', '.join(unused)}")

cg.end()
