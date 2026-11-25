# Exa-MA D7.1: use normal latexmk error handling.
# Layout and reference warnings remain warnings; real build errors fail.
$warnings_as_errors = 0;

# Keep latexmk's default log-wrap width (79). This is a parser setting,
# not a reference-warning filter; zero causes division by zero in latexmk.

# PDF generation mode
$pdf_mode = 1;

# Use pdflatex
$pdflatex = 'pdflatex --shell-escape -interaction=nonstopmode -file-line-error %O %S';

# Maximum number of compilation runs to resolve references
$max_repeat = 5;
