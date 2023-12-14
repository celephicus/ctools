# SMK -- An Hierarchical State Machine Compiler

## History

Originally written in my off time (so not at work) around 2015 to support my day job which was developing controllers
for industrial power supplies. I put it under the MIT license. The only copy of the source I found in an old project
backup. The code was on [Google Code](https://code.google.com/archive/p/smk/), now unfortunately lost, the summary page
was archived but not the content. Thanks Google! This is all I could find. I suppose it might be on Wayback Machine.

	Yet another state machine compiler, targetting vanilla "C", handles nested states.

	SMK is another state machine generator. It takes an input file describing the states, transitions and actions and
	outputs "C" source & header files that can be compiled as is with no editing. It handles any depth of nested
	states, and the time to perform a transition is both very fast and deterministic.

	SMK is targeted squarely at embedded developers who need a simple & fast nested state machine implementation that is
	free of licensing fees.

	SMK is at a very early state, but I am developing on Googlecode to force me to produce a quality tool, rather than a
	collection of half-baked scripts that are for one project alone.

## Other work

[Makina](https://github.com/clnhlzmn/makina) is broadly similar with a DSL as the front end. It wasn't written when I
did smk.

I was influenced by Miro Samek's baroque state machine framework. I actually bought the first edition of his book where
he attempted to explain state concepts using (I kid you not) subatomic particle theory! I think he was a physicist. The
second edition corrects this major error. His implementation defers processing to runtime, it's very clever and his
attention to detail and portability across multiple targets and compilers is commendable, but the phrase *"C’est
magnifique, mais ce n’est pas la guerre."* comes to mind; (attributed to [Pierre Bosquet]
(https://en.wikipedia.org/wiki/Pierre_Bosquet)) though I first encountered it in *Gravity's Rainbow*, where a commando
has it as his personal motto.

There is also [`smc`](https://smc.sourceforge.net/) which I have never used. It's very old and supports lots of language
backends.

## TODO

* Rewrite to use codegen module.
* Add templating to codegen.
* XML as an input format is stupid, I don't know why I did this. JSON would have been better. Change to a DSL. 

