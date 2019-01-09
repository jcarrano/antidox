

.PHONY: doxy-clean clean

VERSION=$(file <tinycbor/VERSION)

xml: Doxyfile.append tinycbor/Doxyfile tinycbor/VERSION
	cat tinycbor/Doxyfile Doxyfile.append \
		| (cd tinycbor/src && VERSION=$(VERSION) doxygen -)

# The file "doxy-xml" will contain the location of the xml directory
doxy-xml: xml
	$(file >$@,$^)

doxy-clean:
	rm -r xml
	rm -r doxy-xml

clean: doxy-clean
