#! /usr/bin/python3

"""Code generator to turn a CSV representation of GPIO signals into a bunch of definitions for a C header file.
"""
import sys, re, os
import csv_parser
import codegen

# pin    sig       func desc     group     apin  ppin port note
# D1/TXD,RS485_TXD,TXD0,RS485 TX,RS485 Bus,J7/12,31,  PD1, TXD/PCINT17,Bootloader

class GPIOParse(csv_parser.CSVparse):
	"Class to handle parsing a CSV file with GPIO definitions."
	def __init__(self):
		csv_parser.CSVparse.__init__(self)
		self.COLUMN_NAMES = 'Pin Sig Func Description Group Apin Ppin Port AltFunc Comment'.split() # pylint: disable=invalid-name
		self.metadata = { 'symbol': {}}
	def handle_directive(self, directive, data):
		directive = directive.lower()
		data += ['', '']
		if directive in 'processor project'.split():
			if directive in self.metadata:
				self.error(f"directive `{directive}' can only appear once")
			self.metadata[directive] = data[0]		# We check this later.
		elif directive == 'symbol':
			macro, expansion = data[:2]
			if not codegen.is_ident(macro):
				self.error(f"bad symbol name `{macro}'")
			self.metadata['symbol'][data[0]] = macro, expansion
		else:
			super().handle_directive(directive, data)
	def on_first_data(self):
		"Validate that we have the correct metadata."
		proc = self.metadata.get('processor', '*none*')
		if proc.lower() != 'avr8':
			self.error(f"cannot use processor `{proc}'")
	def validate_col_Pin(self, pin_name): # pylint: disable=no-self-use,invalid-name
		"Turn a pin name like D1/TXD -> '1'"
		pin_name = pin_name.split('/')[0] 				# Get rid of possible alternate pin name after slash.
		if pin_name.startswith('D'): 				# Arduino pins might start with a D
			pin_name = pin_name[1:]
		return pin_name
	def validate_col_Sig(self, signame): # pylint: disable=no-self-use,invalid-name
		'Not a valid C identifier'
		if signame:
			signame = codegen.ident_allcaps(signame)
		return signame
	def validate_col_Group(self, x): # pylint: disable=no-self-use,invalid-name
		"Set to explicit `None' rather than empty."
		return x if x else 'None'
	def validate_col_Port(self, port): # pylint: disable=no-self-use,invalid-name
		"""Expected either blank or port like `PA3'."""
		# If present then set extra keys to row io_port & io_bit.
		# TODO: Pattern should be configurable for diffferent processors.
		if port.startswith('P'):
			m = re.match(r'(?:(?:P([A-Z]))|(ADC))([0-7])$', port)	# Parse out port, bit from like `PA3'.
			self.add_extra('io_port', m.group(1) or m.group(2))
			self.add_extra('io_bit', int(m.group(3)))
		return port

# Parse...
INFILE = sys.argv[1]
OUTFILE = os.path.splitext(os.path.basename(INFILE))[0] + '.h'	# Write to current directory
cg = codegen.Codegen(INFILE, OUTFILE)
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
cg.add_comment(f'Pin Assignments for {parser.metadata.get("processor", "<none>")}, project: {parser.metadata.get("project", "<none>")}.')

cg.add('enum {')
cg.indent()
for group, pins in pins.items():
	cg.add_comment(group)
	for pindef in pins:
		cg.add(codegen.format_code_with_comments(pindef[0] + ',', pindef[1]))
	cg.add_nl()
cg.add('};', indent=-1, eat_nl=True)

if parser.metadata['symbol']:
	cg.add_comment("Extra symbols from symbol directive.")
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
