
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SOURCEDIR     = source
BUILDDIR      = _build

.PHONY: sphinx-clean doxy-clean clean help view html

VERSION=$(file <tinycbor/VERSION)

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

xml: Doxyfile.append tinycbor/Doxyfile tinycbor/VERSION
	cat tinycbor/Doxyfile Doxyfile.append \
		| (cd tinycbor/src && VERSION=$(VERSION) doxygen -)

# The file "doxy-xml" will contain the location of the xml directory
doxy-xml: xml
	$(file >$@,$^)

sphinx-clean:
	@$(SPHINXBUILD) -M clean "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

doxy-clean:
	rm -rf xml
	rm -rf doxy-xml

clean: doxy-clean sphinx-clean

html: xml
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

sphinx-xml: xml
	@$(SPHINXBUILD) -M xml "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

view: html
	xdg-open _build/html/index.html
