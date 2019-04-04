# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    ?= -j 8
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     ?= .
BUILDDIR      ?= _build

STUBSCRIPT    ?= gen_stubs.py
STUBGEN       ?= python $(STUBSCRIPT)

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help html xml sphinx-clean doxy-clean gen-clean clean view

INDICES ?= generated/file-index.rst generated/group-index.rst

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
html xml pickle: RIOT/doc/doxygen/xml $(INDICES)
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

generated/%-index.rst: RIOT/doc/doxygen/xml $(STUBSCRIPT)
	$(STUBGEN) --$(*F)s $< $(dir $@)

RIOT/doc/doxygen/xml: RIOT/doc/doxygen/Makefile
	$(MAKE) -C RIOT/doc/doxygen xml
	touch $@

# The file "doxy-xml" will contain the location of the xml directory
: RIOT/doc/doxygen/xml
	$(file >$@,$^)

sphinx-clean:
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

doxy-clean:
	rm -rf RIOT/doc/doxygen/xml
	rm -rf doxy-xml

gen-clean:
	rm -rf generated

clean: sphinx-clean doxy-clean gen-clean

view: html
	xdg-open _build/html/index.html
