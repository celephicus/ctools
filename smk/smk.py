#!/usr/bin/python3

""" After parsing the input definition file into a Machine objects with States hanging off it, Smk generates
	a model in tabular form of states x events. This model is elaborated until generating code can be done
	very simply. The model is elaborated in a series of phases, unlike Dr. Evil who doesn't do phases, we do!
	We add arbitrary data to the model by adding a state or event name with a leading ".".
"""

import sys, copy, pprint, re
import smk_parser, smk_format, smk_utils

def model_keys(mmm):
	"Return all model keys that are not *special* (with leading dots)."
	return [k for k in mmm if not k.startswith(".")]
def model_items(mmm):
	"Return all model values that are not *special*."
	return [(k, mmm[k]) for k in model_keys(mmm)]

def _build_transition_map(mmm, mopt):	# pylint: disable=unused-argument
	"""Builds a dict keyed off state names, with each item a dict keyed off event names, holding lists of
		transitions. This takes no account of inheritance from superstates or initial transitions.
		The initial value of the model is the raw parsed machine. """
	new_model = {}
	blank_trans_map = {k: [] for k in mmm.event_list} # Can't use fromkeys(..., []), as only shallow copy of the list.
	for state in mmm.state_map.values():
		st_name = state.name
		new_model[st_name] = copy.deepcopy(blank_trans_map)
		unguarded = []
		for trans in state.transition:
			evdef = [trans.guard, [trans.action] if trans.action else [], trans.target] # Turn action into a list.
			for ev_name in trans.event:
				# Guarded transitions are added first, unguarded are added later, as they must be evaluated last.
				if trans.guard:
					new_model[st_name][ev_name].append(evdef)
				else:
					unguarded.append((ev_name, evdef))
		for ev_name, evdef in unguarded:
			new_model[st_name][ev_name].append(evdef)

	# Add some attributes from the machine.
	new_model['.machine'] = mmm
	  #dict([(k, getattr(mmm, k)) for k in 'name property log verbatim options state_map'.split()])

	return new_model

def get_entry_exit_actions(src, dst):
	"Return list of exit/entry actions for a transition between the src & dst nodes."
	action_nodes = [] # We store just a list of nodes, and fix up the mess in one go at the end of the function.

	# By convention self transitions run their own entry & exit actions.
	if src.name == dst.name:
		action_nodes.append(dst.exit)
		action_nodes.append(src.entry)
	else:
		src_ss = src.get_superstates()
		dst_ss = dst.get_superstates()

		# Remove parents common to both nodes.
		while src_ss and dst_ss and src_ss[-1].name == dst_ss[-1].name:
			src_ss.pop()
			dst_ss.pop()

		# Add exit actions, then entry actions.
		for s_f in src_ss:
			action_nodes.append(s_f.exit)
		for s_r in reversed(dst_ss):
			action_nodes.append(s_r.entry)

	actions = [x.action for x in action_nodes if x] # Get a list of all actions for non-null nodes.
	return [a for a in actions if a] # Remove all empty actions.

def _handle_event_inheritance(mmm, mopt):	# pylint: disable=too-many-locals,too-many-branches
	"""If the transition list for an event is empty, find if any superstates define some transitions and use them
		if found."""
	new_model = copy.deepcopy(mmm)
	state_map = mmm['.machine'].state_map
	for st_name, transmap in model_items(mmm): # Iterate over all states.
		evdefs = []
		for ev_name in model_keys(transmap):
			# If we have no transitions, try up the states until we run out of states or find some transitions.
			for handling_state in state_map[st_name].get_superstates():
				evdefs = mmm[handling_state.name][ev_name]
				if evdefs:
					break

			#print 'State = %s, handling state = %s, event = %s, defs = %s' % (st_name, handling_state.name, ev_name, evdefs)

			# Now we mutate the transitions depending on their target.
			new_model[st_name][ev_name] = []
			for guard, explicit_actions, target in evdefs:
				entry_exit_actions, init_actions, state_change_actions = [], [], []

				# Internal transitions in the state or a superstate are left alone, all we do is the action.
				if not target:
					pass
				# We are targetting another state or have a transitions to self.
				else:
					# Get entry/exit actions to final target.
					entry_exit_actions = get_entry_exit_actions(state_map[st_name], state_map[target])

					# If we have an initial transition then follow it to target until no more initial transitions.
					init_actions, init_target = state_map[target].get_init_actions_state()
					target = init_target.name

					# Add macro to change state to target after any initial transitions ONLY if the transition
					#  is not a transition to self.
					if target != st_name:
						state_change_actions = [f"$SMK_CHANGE_STATE({smk_utils.mk_state_name(target)})"]

				# Add comments to actions if required.
				if mopt.comment_actions:
					if explicit_actions:
						explicit_actions.insert(0, '/* Explicit actions. */')
					if entry_exit_actions:
						entry_exit_actions.insert(0, f"/* Entry/exit actions from state {st_name}. */")
					if init_actions:
						init_actions.insert(0, '/* Initial actions. */')
					if state_change_actions:
						state_change_actions.insert(0, '/* State change actions. */')


				# Add transition to list, Permute the order of actions, if required.
				actions = explicit_actions + entry_exit_actions + init_actions + state_change_actions
				# print '***', st_name, ev_name, `guard`, `actions`, `target`
				if 1: #not (target == st_name and not actions): # pylint: disable=using-constant-test
					new_model[st_name][ev_name].append([guard, actions, target])
	return new_model

def _optimise_transition_sequences(mmm, mopt):	# pylint: disable=too-many-nested-blocks
	new_model = copy.deepcopy(mmm)
	if mopt.optimise >= 1:	# pylint: disable=too-many-nested-blocks
		handlers = {}                   # Keep track of handlers used previously.
		new_model['.goto_labels'] = {}  # Record label targets for later use by code generator.
		label_counter = 0               # Used to generate unique labels.
		for st_name, transmap in model_items(mmm): # Iterate over all states.
			new_model['.goto_labels'][st_name] = {}
			for ev_name, handler in model_items(transmap):
				if handler:
					t_handler = tuple([(g, tuple(a), t) for (g, a, t) in handler]) # Turn into tuple so we can use as a dict key. # pylint: disable=consider-using-generator
					try:
						p_label, p_st_name, p_ev_name = handlers[t_handler] # Handler has appeared before.
						if p_label is None: # If no label then generate a new label.
							p_label = label_counter
							handlers[t_handler][0] = p_label
							# Save the label target for later.
							new_model['.goto_labels'][p_st_name][p_ev_name] = f"        T{p_label:03d}:"
							label_counter += 1
						new_model[st_name][ev_name] = f"goto T{p_label:03d};"  # Replace entire handler with goto.
					except KeyError: # If first time we have seen this handler...
						new_model[st_name][ev_name] = handler
						handlers[t_handler] = [None, st_name, ev_name]

	return new_model

def _remove_empty_transition_lists(mmm, mopt):	# pylint: disable=unused-argument
	for st_name, trans in model_items(mmm):
		for event_name, evdefs in model_items(trans):
			if not evdefs:
				del mmm[st_name][event_name]
	return mmm

def _remove_untargetted_states(mmm, mopt):
	"Removes states that are not targetted by transitions. Removes lots of wasted code. "
	if mopt.optimise >= 2:
		untargetted_states = smk_utils.OrderedSet(model_keys(mmm))
		for st_name, trans in model_items(mmm):
			for ev_name, evdefs in model_items(trans):	# pylint: disable=unused-variable
				for target_state in [e[2] for e in evdefs]:
					untargetted_states.discard(target_state)
		for st_name in untargetted_states:
			print('Deleting state:', st_name, file=sys.stderr)
			del mmm[st_name]
			# del mmm['.machine'].state_map[st_name]
	return mmm

def _generate_in_state_data(mmm, mopt):	# pylint: disable=unused-argument
	mmm['.in_state'] = {}
	for state in mmm['.machine'].state_map.values():
		superstates = [s.name for s in state.get_superstates()]
		mmm['.in_state'][state.name] = superstates
	return mmm

def dump_model(mmm):
	"Dump the model in excruciating detail."
	print('Model:', file=sys.stderr)
	for state, trans_coll in model_items(mmm):	# pylint: disable=unused-variable
		print("{state}:", file=sys.stderr)
		for ev_name, trans in trans_coll.items():
			print(f"  {ev_name}:", file=sys.stderr)
			pprint.pprint(trans, width=120, stream=sys.stderr)

def build_model(mmm, mopt):
	"Successively refine model till we can generate code from it."
	for x in (
	  _build_transition_map,
	  _handle_event_inheritance,
	  _remove_untargetted_states,       # Removes states that are not targetted by transitions.
	  _optimise_transition_sequences,   # Replaces some code with goto's to previous code.
	  _remove_empty_transition_lists,
	  _generate_in_state_data
	  ):
		mmm = x(mmm, mopt)
		if mopt.verbosity:
			print(f"Phase: {x.__name__}", file=sys.stderr)
		if mopt.verbosity >= 2:
			dump_model(mmm)
			print(file=sys.stderr)
	return mmm

if __name__ == '__main__':
	import argparse

	# Our set of output formatters.
	FORMATTERS = {
	  'static-isin': smk_format.Formatter_C_StaticContextIsIn,
	  'static': smk_format.Formatter_C_StaticContext,
#      'global': smk_format.Formatter_C_GlobalContext,
#      'multi': smk_format.Formatter_C_MultiContext,
	  'xml': smk_format.Formatter_XML,
	}

	# Parse command line arguments.
	parser = argparse.ArgumentParser(description='Nested state machine compiler.')
	parser.add_argument('infile', metavar='INFILE', help='Input XML file.')
	parser.add_argument('-o', '--out', dest='outfile', help='Output file name.')
	parser.add_argument('-f', '--format', help='Output file formatter')
	parser.add_argument('-O', '--optimise', type=int, default=0, help='optimisation applied to code')
	parser.add_argument('-c', '--comment-actions', dest='comment_actions', action='store_true',
	  help='add comments to computed action code')

	parser.add_argument('-v', '--verbose', dest='verbosity', default=0, action='store_const', const=1,
	  help='Produce some more verbose output')
	parser.add_argument('-d', '--debug', dest='verbosity', action='store_const', const=2,
	  help='Produce extremely detailed output for debugging only')
	parser.add_argument('-D', '--define', dest='macros', action='append', default=[], help='Define a symbol value.')

	options = parser.parse_args()
	if options.format is None:
		options.format = list(FORMATTERS.keys())[0]
	if options.outfile is None:
		options.outfile = FORMATTERS[options.format].DEFAULT_FILENAMES[0]
	if options.verbosity >= 2:
		print('Options:', options, file=sys.stderr)

	try:
		# Parse input file and emit diagnostics.
		try:
			with open(options.infile, 'rt', encoding="utf-8") as fd_infile:
				machine = smk_parser.parse(fd_infile.read())
		except smk_parser.NodeError as exc:
			sys.exit(f"{options.infile}:{exc.lineno}: error: {exc.msg}")

		if options.verbosity >= 2:
			print("Options from model: ", tuple(machine.options.content) if machine.options else '<none>', file=sys.stderr)
		#print machine.state[0]
		# Choose an output format.
		formatter = FORMATTERS[options.format](options.outfile, options)

		# Build table of macros.
		for macro_def in options.macros:
			m = re.match(r'([a-z_]+)\s*=\s*(.*)$', macro_def, re.I)
			if not m:
				raise smk_parser.NodeError(f"Require an `=` in the -D option `{macro_def}'.")
			formatter.symbols[m.group(1).strip().upper()] = m.group(2)
		if options.verbosity >= 2:
			print("Predefined symbols:", file=sys.stderr)
			for macro, exp in formatter.symbols.items():
				print(f' {macro} = {exp}', file=sys.stderr)
			print(file=sys.stderr)

		# Build model.
		model = build_model(machine, options)

		# Generate output
		try:
			formatter.generate(model)
		except:
			formatter.abort()
			raise
		else:
			formatter.close()
	except smk_parser.NodeError as exc:
		sys.exit("{options.infile}:0 error: {str(exc)}")
