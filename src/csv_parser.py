""" Simple parser for CSV files that does many of the common tasks needed for using CSV files as input for code generation.
	Provides a base class CSVparse that must be subclassed for an actual parser.
"""

import csv
import sys
import re
import os

class CSVparseError(Exception):
	"Exception raised by CSVparse parser and subclasses."
	pass

class CSVparse:
	"""Base class to build a parser for CSV file.

	Spreadsheets are excellent for dealing with data in a tabular format, with the bonus that they can be carefully edited in a text editor.
	I found myself rewriting the same code to read CSV files in a variety of formats for "C" code generation. An example is below (column
	titles on first line):

	NAME		PORT	FUNCTION		DESCRIPTION
	----		----	--------		-----------
	LED			PA3		output			"Blinky LED"
	SW_1		PB0		input,pullup	"Switch 1"
	RS232_TX	PD1		TXD				"RS232 serial transmit"

	This defines port pin allocation for a project, and tags each pin as having a function. This can be used to autogenerate a header file with
	pin definition, and a set of macros for accessing each pin. The advantage is that this critical information is defined in one place, in a
	form where it can be shared without forcing non-programmers to read code.

	A problem was that the data in the CSV file required a bit of processing and validation before it could be used. For example, only a few options
	are available for the FUNCTION column, and the pin NAME must be unique, and so on. What to do about missing columns, or leading/trailing spaces?

	So this class can be used to write parsers that clean the input of various inconsistencies, and then use a custom function to validate that each
	value is valid, this can be a simple regex or a more complex function that converts the item from a string to say a list. Attention has been
	given to providing good error messages with file & line information. Each row in the input that contains data results in an item in the `data'
	attribute. There is also provision for directives, commands that are not data but are read by the parser, these can be used to modify
	behaviour or add data to an attribute in the derived class.

	To construct a basic parser, subclass CSVparse and set COLS to the column names. This is the test code at the end of this file.

	class MyParser(CSVparse):
		COLS = 'Name Port Function Description'.split()
		def __init__(self):
			super.__init__()

	This still does quite a lot, the example above is parsed to the `data' attribute as:
	[ {'Name': 'LED', 'Port': 'PA3', 'Function': 'output', 'Description': 'Blinky LED'},
	  {'Name': 'SW_1', 'Port': 'PB0', 'Function': 'input,pullup', 'Description': 'Switch 1'},
	  {'Name': 'RS232_TX', 'Port': 'PD1', 'Function': 'TXD"RS232 serial transmit"', 'Description': ''} ]

	But there is no validation, any values are accepted. If we want to mandate that the Name column must be a "C" identifier, then we just add
	a regex, which the column must match.
		validate_col_Name = r'^[A-Z_][A-Z_0-9]*$'

	Or we might want the Port column to always be upper case:
		def validate_col_Port(self, d):
			return d.upper()

	Or we might want the Function column split out into items separated by commas and validated that they are only certain values:
		def validate_col_Function(self, d):
			ffs = [x.strip() for x in d.split(',')]
			if sum(x not in 'input output pullup TXD'.split() for x in ffs): raise ValueError
			return ffs


	The goal is to easily provide a sanitised set of data to  following process, usually code generation.

	A detailed breakdown of the processing is given below. This is worth studying as the order of steps can make a difference in some cases.

	The input file presented as a file object or a filename is read row-by-row by the csv module.
	  All cells have leading and training whitespace removed.
	  Blank lines are ignored
	  Rows with the first cell having a `#' as the first character are comments and are ignored.
	  Starting from the rightmost, those cells that are empty are removed.
	  If the row has less cells than the number of columns, extra empty cells are added.
	  Rows with a `@' as the first character are directives and may be processed by subclasses. By default the parser issues a warning.
	  Call method validate_column_count() which allows subclasses to check extra columns. By default the parser issues a warning.
	  Convert the row data into a dict keyed off the names in COLS.
	  Call method preprocess() to allow subclasses to do some preprocessing on the dist.
	  Add the dict to the data attribute.

	"""

	def __init__(self):
		"""Sets up a new parser, must be called by subclasses if they have an __init__() method.
			HINT: use `super().__init__(...)'."""
		self.filename = None	# Filename being read from.
		self.lineno = 0			# The current line being read is held as an attribute for error message formatting.
		self.data = []			# Data from each row ends up here as a dict with keys from the COLS class attribute.
		self._extra	= {}		# Used by validators to add extra key/values to the row data.
		self.metadata = {}		# Data from directives might end up here.

	def get_error_msg(self, category, msg):
		"""Called from read, formats an error message."""
		return f'{os.path.basename(__file__)}: Input file {self.filename}:{self.lineno} {category} {msg}.'
	def warning(self, msg):
		"""Print a warning message."""
		print(self.get_error_msg('warning', msg), file=sys.stderr)
	def error(self, msg):
		"""Print an error message."""
		raise CSVparseError(self.get_error_msg('error', msg))
	def add_extra(self, key, val):
		"""Used by validators to add some extra data to the row dict."""
		self._extra[key] = val

	# Directives start with this string. Args are padded with blanks up to the maximum given.
	DIRECTIVE_LEADER_STR = '@'	# pylint: disable=invalid-name
	MAX_DIRECTIVE_ARGS = 2
	def handle_unknown_directive(self, directive, data):	# pylint: disable=unused-argument
		"""Override to do something creative with directives."""
		self.error(f"unexpected directive `{directive}'")

	# Set names for all columns. Any extra columns in input are ignored.
	COLUMN_NAMES = ()	# pylint disable=invalid-name

	def validate_column_count(self, count):
		"""Allows you to do things like warning of extra columns. Default is to insist on the same number as items in COLUMN_NAMES."""
		if count != len(self.COLUMN_NAMES):
			self.warning(f"extra columns ignored: expected {len(self.COLUMN_NAMES)}, got {count}")
	def preprocess(self, row):
		"""Subclasses might require some preprocessing of the row data."""
		pass
	def on_first_data(self):
		"Called for first row of data. Allows validation of metadata."
		pass

	def read(self, fp_or_fn):		# pylint: disable=too-many-branches
		"""Read a CSV file from a filename or file object and parse it. Details in the class doc."""
		if isinstance(fp_or_fn, str):
			self.filename = fp_or_fn
		else:
			self.filename = getattr(fp_or_fn, 'name', '<none>')

		with open(self.filename, 'rt', encoding='utf-8') if isinstance(fp_or_fn, str) else fp_or_fn as csvfile:
			reader = csv.reader(csvfile)
			for self.lineno, row in enumerate(reader, start=1):
				#print('\n', row, end='')
				row = [item.strip() for item in row]				# Strip off surrounding blanks.

				while row and (not row[-1] or row[-1].isspace()):	# Remove empty items from end of row.
					row.pop()
				if not row:	continue								# Ignore blank lines.
				if row[0].startswith('#'): continue					# Ignore comments

				# Is a directive? Either call subclass handler or unknown handler.
				if m := re.match(rf'{self.DIRECTIVE_LEADER_STR}(.*)$', row[0]):
					directive = m.group(1).lower()
					args = row[1:] + ['']*self.MAX_DIRECTIVE_ARGS
					d_handler = getattr(self, 'handle_directive_' + directive, self.handle_unknown_directive)
					d_handler(directive, args)
					continue

				if not self.data:									# On first row of data, call validator.
					self.on_first_data()

				while len(row) < len(self.COLUMN_NAMES):			# Pad out to expected number of columns if less.
					row.append('')

				self.validate_column_count(len(row))				# Allow subclasses to complain for extra columns.

				row = dict(zip(self.COLUMN_NAMES, row))				# Turn row into a dict.
				self.preprocess(row)								# Let subclasses do a bit of preprocessing.

				# Validate/process each item in the row up to expected columns, extra columns ignored.
				self._extra = {}		# Clear extra values dict in case validators want to add a bit extra.
				for c_name in self.COLUMN_NAMES:
					validator = getattr(self, 'validate_col_' + c_name, None)
					if validator is None: continue		# No validator.

					error_msg_leader = f'column `{c_name}\'="{row[c_name]}" invalid: '
					if isinstance(validator, str):		# String implies match against regex.
						if not re.search(validator, row[c_name]):
							self.error(error_msg_leader + f"did not match `{validator}'")
					else:								# Not a string, try calling it.
						try:
							row[c_name] = validator(row[c_name]) # This will either return a new value or raise an exception.
						# Validators could raise any exception, unusual to catch the base class exception...
						except Exception as validator_exc:	# pylint: disable=broad-except
							reason = validator.__doc__		# Get exception message
							if not reason:	reason = str(validator_exc) # Or make one up if none.
							self.error(error_msg_leader + reason)
				row.update(self._extra)		# Add any extra data generated by validators.
				self.data.append(row)

# pylint: disable=missing-function-docstring,missing-class-docstring,consider-using-with,invalid-name,no-self-use
if __name__ == "__main__":
	"""Sample parser, try changing values in the source string and seeing what errors you get."""
	from io import StringIO
	import pprint

	class TParse(CSVparse):
		def __init__(self):
			CSVparse.__init__(self)
			self.COLUMN_NAMES = 'Name Port Function Description'.split()
		validate_col_Name = r'^[A-Z_][A-Z_0-9]*$'
		def validate_col_Port(self, d):
			return d.upper()
		def validate_col_Function(self, d):
			ffs = [x.strip() for x in d.split(',')]
			if sum(x not in 'input output pullup TXD'.split() for x in ffs): raise ValueError
			return ffs

	fp_in = StringIO('''\

#	NAME		PORT	FUNCTION		DESCRIPTION
@directive
LED,PA3,output,"Blinky LED"
SW_1,pb0,"input,pullup","Switch 1"
RS232_TX,PD1,TXD,"RS232 serial transmit"
''')
	tparser = TParse()
	try:
		tparser.read(fp_in)
	except CSVparseError as e:
		print(e)
	pprint.pprint(tparser.data)
