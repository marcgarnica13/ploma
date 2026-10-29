# Makefile for building the LLNCS manuscript
#
# Usage:
#   make build   # generate samplepaper.pdf (pdflatex -> bibtex -> pdflatex x2)
#   make clean   # remove LaTeX build artifacts (keeps the PDF)
#   make cleanall# remove build artifacts AND the PDF
#   make         # same as `make build`

LATEX   = pdflatex
BIBTEX  = bibtex
LFLAGS  = -interaction=nonstopmode -halt-on-error
MAIN    = samplepaper

.PHONY: build clean cleanall

build: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex mybib.bib
	$(LATEX) $(LFLAGS) $(MAIN).tex
	$(BIBTEX) $(MAIN)
	$(LATEX) $(LFLAGS) $(MAIN).tex
	$(LATEX) $(LFLAGS) $(MAIN).tex

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out $(MAIN).toc

cleanall: clean
	rm -f $(MAIN).pdf
