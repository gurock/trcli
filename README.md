trcli - The TestRail CLI client
===============================

TR CLI (trcli) is a command line tool for interacting with TestRail.

Parsers
=======

Parsers are located in `/trcli/readers/`. To add new parser please read desired file and fill required dataclasses with the data (located in `/trcli/data_classes/`).

Available parsers:

* XML Junit files compatibile with Jenkins and pytest reporting schemas
* ...
