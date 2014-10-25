#!/usr/bin/perl
use warnings;
use strict;
use CGI qw/:all/;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);
# use CGI::Cookie;
warningsToBrowser(1);
use Data::Dumper;

if ($ENV{'QUERY_STRING'} eq "" and  (not defined param('login_details'))) {
	print_index();
	exit (0);
}

if (defined param('login_details')) {
	my $username = param('username');
	my $password = param ('password');
	my $correct = validateLogin($username, $password);
	if ($correct == 1) {
		param('login',"SUCCESSFUL");
		print_index("",$username);
	} else {
		my $login_fail_status = determineStatus ($correct);
		param('login',"Attempt_Unsuccessful");
		# print header,start_html,p("$login_fail_status"),end_html;
		# exit (1);
		print_index ($login_fail_status,"");
	}
}

if (url_param('request') eq "logout") {
	param('login',"FALSE");
	print_index();
}

if (url_param('page') eq "browse_page") {
	print header;
	open (BROWSE_PAGE,"<browse.html") or die "Cannot open browse.html: $!\n";
	while (<BROWSE_PAGE>) {
		print;
	}
} 

# print_index ($login_fail_status,$username');
sub print_index {
	my ($login_fail_status, $username) = @_;
	print header;
	print start_html(-title=>"LOVE2041",
		             -style=>{'src'=>'navbar.css'},
	);
	open (NAVBAR,"navbar.html") or die "Cannot open navbar.html\n";
	while (<NAVBAR>) {
		print;
	}
	param('login',"FALSE") if (not defined param('login'));
	if (param('login') eq "FALSE") {
		open(LOGIN_INPUT,"<login_input.html") or die "Could not open login_input.html, $!\n";
		while (<LOGIN_INPUT>) {
			print;
		}
		close (LOGIN_INPUT);
		print hidden('login');
	} elsif (param('login') eq "Attempt_Unsuccessful") {
		#the user failed at login, will check for faliure details
		if ($login_fail_status eq "UNKNOWN_USERNAME") {
			print h2("Unknown Username");
			open(LOGIN_INPUT,"<login_input.html") or die "Could not open login_input.html, $!\n";
			while (<LOGIN_INPUT>) {
				print;
			}
			close (LOGIN_INPUT);
			print hidden ('login');
		} elsif ($login_fail_status eq "INCORRECT_PASSWORD") {
			print h2("Incorrect password");
			open(LOGIN_INPUT,"<login_input.html") or die "Could not open login_input.html, $!\n";
			while (<LOGIN_INPUT>) {
				print;
			}
			close (LOGIN_INPUT);
			print hidden('login');
		}
	} elsif (param('login') eq "SUCCESSFUL") {
		print h2("Welcome $username");
		print hidden('login');
	}
	print end_html();
}

sub validateLogin {
	my ($username, $password) = @_;
	return -1 if ((!defined $username) or (!defined $password));
	return -2 if (not -d "students/$username");
	return -3 if (not -f "students/$username/profile.txt");
	open (PROFILE,"<students/$username/profile.txt") or die "Cannot open the profile, $!\n";
	my $found = 0;
	my $userPass = "";
	while (my $line = <PROFILE>) {
		chomp $line;
		if ($line =~ m/^\s*password:\s*$/) {
			$found = 1;
			next;
		}
		if ($found) {
			$line =~ m/\s+(.+)\s*$/;
			$userPass = $1;
			last;
		}
	}
	close (PROFILE);
	($userPass eq $password)? return 1 : return -4;
}

sub determineStatus {
	my $status = $_[0];
	if ($status == -1) {
		return "INSUFFICIENT INFO";
	} elsif ($status == -2) {
		return "UNKNOWN_USERNAME";
	} elsif ($status == -4) {
		return "INCORRECT_PASSWORD";
	}
}