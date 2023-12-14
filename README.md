# CTOOLS

A collection of scripts that I use a lot for embedded "C".

These are cleaned up versions of scrappy things that I have been using for years over various jobs. In general they automate the boring stuff by code generation and string templating.

## SMK

This is the big one. It reads a simple representation of a heirarchial state machine (in XML, sorry) and generates "C" code to run it.  
An early version from around 2014 was on Google code with an MIT license, but the Google people did not see fit to archive the code and issue list, which was extensive as I recall. So I resurrected the oldest copy I could find from an old project backup. Then I cleaned it up a bit and fixed some bugs so that I could use it. 

It really needs a full rewrite, unit tests and a new input format. I can't recall why I used XML as the input format, probably I was writing a lot of XML manually so had just developed antibodies to it's general loquacity and need to escape a few characters that are annoyingly common in C source, eg: 

    if (a &amp;&amp; b)

