#!/usr/bin/env perl
use strict;
use warnings;

my $path = shift @ARGV or die "usage: $0 path/to/main.tex\n";
open my $in, '<', $path or die "cannot read $path: $!\n";
local $/;
my $text = <$in>;
close $in;

die "floats already collected at manuscript end\n"
    if $text =~ /% BEGIN END-MATTER TABLES/;

my (@tables, @figures);
$text =~ s{
    \\begin\{(table\*?|figure\*?)\}\[[^\]]*\]
    (.*?)
    \\end\{\1\}
}{
    my ($kind, $body) = ($1, $2);
    my $block = "\\begin{$kind}[p]$body\\end{$kind}";
    if ($kind =~ /^table/) { push @tables, $block; }
    else                   { push @figures, $block; }
    '';
}gsex;

die "expected five tables, found " . scalar(@tables) . "\n"
    unless @tables == 5;
die "expected thirteen figures, found " . scalar(@figures) . "\n"
    unless @figures == 13;

my $end_matter = join(
    "\n",
    '\\FloatBarrier',
    '\\bibliography{References}',
    '\\clearpage',
    '% BEGIN END-MATTER TABLES',
    '\\section*{Tables}',
    join("\n\n", @tables),
    '\\clearpage',
    '% END END-MATTER TABLES',
    '% BEGIN END-MATTER FIGURES',
    '\\section*{Figures}',
    join("\n\n", @figures),
    '\\clearpage',
    '% END END-MATTER FIGURES',
    '\\end{document}',
    '',
);

$text =~ s{
    \\FloatBarrier\s*
    \\bibliography\{References\}\s*
    \\end\{document\}\s*\z
}{$end_matter}x
    or die "could not locate bibliography/end-document marker\n";

open my $out, '>', $path or die "cannot write $path: $!\n";
print {$out} $text;
close $out;
print "Moved " . scalar(@tables) . " tables and " . scalar(@figures)
    . " figures to the manuscript end.\n";
