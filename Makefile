BASE=template
DIRECTORY=numpexDeliverable
bib:
	bibtool  -v -d -s -- 'preserve.key.case=on' -x $(BASE).aux > $(BASE)-new.bib
	mv $(BASE).bib	$(BASE)-old.bib	
	mv $(BASE)-new.bib $(BASE).bib

#dist: bib
dist:
	cd .. && tar hcfvz /tmp/$(DIRECTORY).tgz --exclude-from=$(DIRECTORY)/exclude.txt $(DIRECTORY)/ 

zip:
	cd .. && zip -r /tmp/$(DIRECTORY) $(DIRECTORY)/ -x@$(DIRECTORY)/exclude.txt 

distzip: bib zip

diffpdf:
	latexdiff-vc --git -r $(BASE).tex --pdf 
	-rm $(BASE)-diff.aux 
	-rm $(BASE)-diff.log
	-rm $(BASE)-diff.blg
	-rm $(BASE)-diff.bbl

## NB: please make sure a tag to the submitted version has been added. E.g.:
##
##     git tag -a submitted de73354f15603ceef470eebb3cac28f16ba014fd
##
diffsubmitted: ARGS=submitted
diffsubmitted: diffversion
	@echo Generated diff between the current and submitted versions $(BASE)-diff${ARGS}.pdf

## run as, for instance:
##      make ARGS=de73354f15603ceef470eebb3cac28f16ba014fd diffversion
##
diffversion:
	mkdir -p /tmp/${ARGS}
	cp -a * /tmp/${ARGS}
	git show ${ARGS}:$(BASE).tex > /tmp/${ARGS}/$(BASE).tex
	git show ${ARGS}:$(BASE).bib > /tmp/${ARGS}/$(BASE).bib
	cd /tmp/${ARGS}/ && pdflatex $(BASE).tex &&  bibtex $(BASE)
	latexdiff-vc --git -r ${ARGS}  $(BASE).tex 
	latexdiff --exclude-textcmd="href" /tmp/${ARGS}/$(BASE).bbl $(BASE).bbl >/tmp/tmp.bbl
	mv /tmp/tmp.bbl $(BASE)-diff${ARGS}.bbl
	-pdflatex --interaction nonstopmode $(BASE)-diff${ARGS}.tex
	-pdflatex --interaction nonstopmode $(BASE)-diff${ARGS}.tex
	-pdflatex --interaction nonstopmode $(BASE)-diff${ARGS}.tex
	-rm $(BASE)-diff${ARGS}.aux 
	-rm $(BASE)-diff${ARGS}.log
	-rm $(BASE)-diff${ARGS}.blg
	-rm $(BASE)-diff${ARGS}.bbl
	-rm $(BASE)-diff${ARGS}.spl

## untested; don't use
distbib:
	cat $(BASE).tex | perl -e 'while(<>){if (/(\\bibliography{.+?})/) {print "\%\%$1\n"; print "\\bibliography{$(BASE)}\n"} else {print;} }' > $(BASE)-new.tex

## svn propset svn:keywords ’Id Author Date Rev URL’ *.tex
