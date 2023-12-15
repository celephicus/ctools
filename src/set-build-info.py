#! /usr/bin/python3

'''
Search for lines like these:
#define CFG_BUILD_NUMBER 2						# Increment number.
#define CFG_BUILD_TIMESTAMP "20220925T112148"	# Set new datestamp.
Fail if either not found.
'''

import re, time, argparse
import codegen

INFILE_DEFAULT = 'project_config.h'

# Parse command line arguments.
arg_parser = argparse.ArgumentParser(description='Updates build number & date in #defined symbols in C header file.')
arg_parser.add_argument('infile', default=INFILE_DEFAULT, nargs='?', help='Input file, will be overwritten.')

codegen.Verbosity.add_argparse_options(arg_parser)
options = arg_parser.parse_args()
codegen.Verbosity.parse_options(options)	# Sort out verbosity.

# Read input file.
cg = codegen.Codegen(options.infile, options.infile)
text = cg.begin()

# Match & update symbols. Note that symbol must be preceded by a `#define' to be replaced, as the symbol is likely
#  referenced after definition in the file.
UPDATES = (
	(lambda m: time.strftime('CFG_BUILD_TIMESTAMP "%Y%m%dT%H%M%S"'), r'(?<=#define\s)CFG_BUILD_TIMESTAMP\s+.*$'),
	(lambda m: f"CFG_BUILD_NUMBER {int(m.group(1)) + 1}", r'(?<=#define\s)CFG_BUILD_NUMBER\s*(\d+)'),
)

for repl, regex in UPDATES:
	text, n_sub = re.subn(regex, repl, text, flags=re.M)
	if n_sub != 1:
		codegen.error(f"expected line like `{regex}'")

# This rewrites and closes the file. Thanks codegen!
cg.add(text)
cg.end()
