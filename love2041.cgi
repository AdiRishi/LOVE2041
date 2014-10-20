#!/usr/bin/perl
use warnings;
use strict;
use CGI qw/:all/;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);
warningsToBrowser(1);
use Data::Dumper;

browse_page() if (url_param('page') eq "browse_profile");


sub browse_page {
	
}
