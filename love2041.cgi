#!/usr/bin/perl
use warnings;
use strict;
use CGI qw/:all/;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);
warningsToBrowser(1);
use Data::Dumper;

print_index() if (not defined $ENV{'QUERY_STRING'});
browse_page() if (url_param('page') eq "browse_profile");


sub browse_page {
	print header;
	print start_html('User profiles');
	foreach my $folder (glob "students/*") {
		print p("$folder");
	}
	print end_html;
}

sub print_index {
	print header;
	open (INDEX,"../LOVE2041/index.html") or die "Cannot open index.html\n";
	while (<INDEX>) {
		print;
	}
}