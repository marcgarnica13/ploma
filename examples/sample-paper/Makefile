MAIN = main
LATEX = pdflatex -interaction=nonstopmode -file-line-error
BIBTEX = bibtex

.PHONY: build clean cleanall

build: $(MAIN).pdf

$(MAIN).pdf: $(MAIN).tex sections/*.tex refs.bib figures/fig1.pdf
	$(LATEX) $(MAIN)
	$(BIBTEX) $(MAIN)
	$(LATEX) $(MAIN)
	$(LATEX) $(MAIN)

clean:
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).blg $(MAIN).log $(MAIN).out

cleanall: clean
	rm -f $(MAIN).pdf
	rm -rf build
