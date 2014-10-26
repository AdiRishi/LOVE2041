#!/usr/bin/perl --
use warnings;
use strict;
use CGI qw/:all/;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);
use CGI::Cookie;
warningsToBrowser(1);
use Data::Dumper;
use HTML::Template;

use constant {
	NUM_BROWSE_ROWS => 4,
	BOX_PER_ROW => 4,
	FIELD_LINE => 1,
	FIELD_LINE_LEVEL1 => 2,
	FIELD_LINE_LEVEL2 => 3,
	VALUE_LINE => -1,
};

my %cookies = CGI::Cookie->fetch;
if (not defined $cookies{'login_cookie'}) {
	my $newCookie = CGI::Cookie->new(-name=>'login_cookie',
									-value => {
										username => 'UNSET',
										login_status => 'LOGGED_OUT'
										},
									-expires => "+30m",
									);
	my $template = HTML::Template->new(filename=>'login.html');
	print "Set-Cookie: $newCookie\n";
  	print "Content-Type: text/html\n\n";
  	print $template->output();
  	exit (0);
} else {
	my %loginValue = $cookies{'login_cookie'}->value;
	if (($loginValue{'login_status'} eq "LOGGED_OUT")
		and (not defined param('login_submit'))) {
		my $template = HTML::Template->new(filename=>'login.html');
		print header;
		print $template->output();
		exit (0);
	}
}

if (defined param('login_submit')) {
	my $validation_code = validateLogin(param('username'),param('password'));
	if ($validation_code != 1) {
		my $template = HTML::Template->new(filename=>'login.html');
		my $error_status = determineStatus ($validation_code);
		if ($error_status eq "UNKNOWN_USERNAME") {
			$template->param(ERROR=>'1',Uname=>'1');
		} elsif ($error_status eq "INCORRECT_PASSWORD") {
			$template->param(ERROR=>'1',pass=>'1');
		} else {
			$template->param (ERROR=>'1',info=>'1');
		}
		print header;
		print $template->output();
	} else {
		my $login_cookie = $cookies{'login_cookie'};
		$login_cookie->value({username => param('username'),login_status => 'LOGGED_IN'},);
		print "Set-Cookie: $login_cookie\n";
  		print "Content-Type: text/html\n\n";
  		print start_html,h1("Check the cookie");
  		print end_html();
	}
}

#the following part of the code will only execute if the user is logged in
print header, start_html, h1("You are now logged in"),end_html;

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

sub createDatabase {
	my %userDatabase = ();
	my $key1 = undef;
	my $key2 = undef;
	my $lineType;
	foreach my $username (glob "students/*") {
		foreach my $filename (("profile","preferences")) {
		open (FILE,"<$username/$filename.txt") or die "Cannot open $username/$filename.txt, $!\n";
		my @input = <FILE>;
		my $counter = 0;
		while ($counter <= $#input) {
			my $line = $input[$counter];
			chomp $line;
			$lineType = getLineType ($line);
			if ($lineType > 0) {
				die "Error in line parsing, key corruption\n" if ($lineType == FIELD_LINE_LEVEL2 and (not defined $key1));
				if ($lineType == FIELD_LINE_LEVEL1) {
					if (defined $key1) {
						$key1 = undef;
						$key2 = undef;
						next;
					}
					$key1 = extractData ($line, $lineType);
				} else {
					$key2 = extractData ($line, $lineType);
				}
			} else {
				if (defined $key2) {
					if (defined $userDatabase{$username}{$filename}{$key1}{$key2}) {
						if (ref($userDatabase{$username}{$filename}{$key1}{$key2}) eq "ARRAY") {
							push @{$userDatabase{$username}{$filename}{$key1}{$key2}},extractData ($line, $lineType);
						} elsif (ref($userDatabase{$username}{$filename}{$key1}{$key2}) eq "") {
							my $tempStore = $userDatabase{$username}{$filename}{$key1}{$key2};
							$userDatabase{$username}{$filename}{$key1}{$key2} = [];
							push @{$userDatabase{$username}{$filename}{$key1}{$key2}}, $tempStore;
							push @{$userDatabase{$username}{$filename}{$key1}{$key2}}, extractData ($line, $lineType);
						}
					} else {
						$userDatabase{$username}{$filename}{$key1}{$key2} = extractData ($line, $lineType);
					}
				} elsif (defined $key1) {
					if (defined $userDatabase{$username}{$filename}{$key1}) {
						if (ref($userDatabase{$username}{$filename}{$key1}) eq "ARRAY") {
							push @{$userDatabase{$username}{$filename}{$key1}},extractData ($line, $lineType);
						} elsif (ref($userDatabase{$username}{$filename}{$key1}) eq "") {
							my $tempStore = $userDatabase{$username}{$filename}{$key1};
							$userDatabase{$username}{$filename}{$key1} = [];
							push @{$userDatabase{$username}{$filename}{$key1}}, $tempStore;
							push @{$userDatabase{$username}{$filename}{$key1}}, extractData ($line, $lineType);
						}
					} else {
						$userDatabase{$username}{$filename}{$key1} = extractData ($line, $lineType);
					}
				}
			}
			$counter++;
		}
		}
	}
	# print Dumper \%userDatabase;
}

sub getLineType {
	my $line = $_[0];
	my $lineType;
	my $returnVal;
	if ($line =~ m/^(\s*)\S+:\s*$/) {
		my $indent = $1;
		if ($indent eq "") {
			$returnVal = FIELD_LINE_LEVEL1;
		} elsif ($indent eq "\t") {
			$returnVal = FIELD_LINE_LEVEL2;
		} else {
			die "Error in line parsing\n";
		}
	} else {
		$returnVal = VALUE_LINE;
	}
	return $returnVal;
}

sub extractData {
	my $line = $_[0];
	my $type = $_[1];
	if ($type > 0) {
		$line =~ m/^\s*(.+):\s*$/;
		return $1;
	} else {
		$line =~ m/^\s*(.+)\s*$/;
		return $1;
	}
}
