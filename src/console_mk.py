#! /usr/bin/python3

"""Open an input file and write it back with text like `case /** <xxx> **/ 0xb58b:'
	having the hex chars replaced with a hash of the printable chars <xxx>.
"""

import re
import sys
import glob
import codegen

def do_hash(cmd_s):
	"Produce a 16 bit hash from a string."
	# Hash constants from Wikipedia. Apparently 32 works just as well.
	HASH_START, HASH_MULT = 5381, 33 # pylint: disable=invalid-name
	hash_c = HASH_START
	for cmd_ch in cmd_s:
		hash_c = ((hash_c * HASH_MULT) & 0xffff) ^ ord(cmd_ch)
	return hash_c

def subber_hash(m):
	"Produce a C snippet containing a 16 bit hash from a string in a regex match."
	cmd_s = m.group(1).upper()
	return f'/** {cmd_s} **/ 0x{do_hash(cmd_s):04x}'

for infile in glob.glob(sys.argv[1], recursive=True):
	cg = codegen.Codegen(infile, infile)
	text = cg.begin()

	cg.add(re.sub(r'/\*\*\s*(\S+)\s*\*\*/\s*(0[x])?([0-9a-f]*)', subber_hash, text, flags=re.I))
	cg.end()
