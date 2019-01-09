# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help html xml sphinx-clean doxy-clean clean view

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
html xml: RIOT/doc/doxygen/xml
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

RIOT/doc/doxygen/xml:
	$(MAKE) -C RIOT/doc/doxygen xml

# The file "doxy-xml" will contain the location of the xml directory
doxy-xml: RIOT/doc/doxygen/xml
	$(file >$@,$^)

sphinx-clean:
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

doxy-clean:
	rm -rf RIOT/doc/doxygen/xml
	rm -rf doxy-xml

clean: sphinx-clean doxy-clean

view: html
	xdg-open _build/html/index.html
