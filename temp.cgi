#!/usr/bin/perl
use warnings;
use strict;
use CGI qw/:all/;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);
# use CGI::Cookie;
warningsToBrowser(1);
use Data::Dumper;
use HTML::Template;

use constant {
	NUM_BROWSE_ROWS => 4,
	BOX_PER_ROW => 4,
};

# if ($ENV{'QUERY_STRING'} ne "" and  (param('login') == undef or param('login') ne "SUCCESSFUL")) {
# 	# print start_html,p("First if"),end_html;
# 	# exit (1);
# 	print_index();
# 	exit (0);
# }

if ($ENV{'QUERY_STRING'} eq "" and (not defined param('login_details'))) {
	# print start_html,p("Second if"),end_html;
	print_index ();
	exit (0);
}

if (defined param('login_details') and param('login') ne "SUCCESSFUL" and $ENV{'QUERY_STRING'} eq "") {
	# print start_html,p("Third if"),end_html;
	my $username = param('username');
	my $password = param ('password');
	my $correct = validateLogin($username, $password);
	if ($correct == 1) {
		param('login',"SUCCESSFUL");
		print_index("",$username);
	} else {
		my $login_fail_status = determineStatus ($correct);
		param('login',"Attempt_Unsuccessful");
		print_index ($login_fail_status,"");
	}
}

if (url_param('request') eq "logout") {
	# print start_html,p("Fourth if"),end_html;
	# exit (1);
	param('login',"FALSE");
	print_index();
}

if (url_param('page') eq "browse_page") {
	# print start_html,p("Fifth if"),end_html;
	# exit (1);
	print header;
	param('browse_index', 0) if (not defined param('browse_index'));
	my @students = glob ("students/*");
	print start_html({
      -head=>Link({-rel=>'stylesheet', -type=>'text/css', -href=>'browse.css'}).
      Link({-rel=>'stylesheet', -type=>'text/css', -href=>'navbar.css'}),});
	open (NAVBAR, "<navbar.html");
	while (<NAVBAR>) {
		print;
	}
	close (NAVBAR);
	my $template = HTML::Template->new(filename=>'user_box.tmpl');
	my $rows = 0;
	my $profile_num = param('browse_index');
	while ($rows < NUM_BROWSE_ROWS) {
		my @userData = ();
		my $tempCount = 0;
		while ($tempCount < BOX_PER_ROW) {
			push @userData, {};
			$tempCount++;
		}
		$tempCount = 0;
		while ($profile_num < param('browse_index') + BOX_PER_ROW) {
			my $foundGener = 0;
			my $foundUname = 0;
			# print "THE PROFILE NUMBER IS $profile_num\n";
			# print "THE PROFILE IS $students[$profile_num]\n";
			open (PROFILE, "<$students[$profile_num]/profile.txt") or die "Cannot open $students[$profile_num]/profile.txt, $!\n";
			if (-f "$students[$profile_num]/profile.jpg") {
				${$userData[$tempCount]}{'image_src'} = "$students[$profile_num]/profile.jpg";
			}
			while (my $line = <PROFILE>) {
				chomp $line;
				# print "THE PLAIN CORE LINE : $line\n";
				if ($line =~ m/^\s*gender:\s*$/) {
					# print $line,"This is the gender line\n";
					$foundGener = 1;
					next;
				}
				if ($line =~ m/^\s*username:\s*$/) {
					# print $line,"This is the username line\n";
					$foundUname = 1;
					next;
				}
				if ($foundGener and (not defined ${$userData[$tempCount]}{'user_gender'})) {
					# print "This is the user gender VALUE line\n",$line,"\n";
					$line =~ m/\s*(.+)\s*/;
					${$userData[$tempCount]}{'user_gender'} = $1;
					next;
				}
				if ($foundUname and (not defined ${$userData[$tempCount]}{'user_name'})) {
					# print $line,"This is the user name VALUE line\n",$line,"\n";
					$line =~ m/\s*(.+)\s*/;
					${$userData[$tempCount]}{'user_name'} = $1;
					next;
				}
				last if ($foundGener and $foundUname);
			}
			close (PROFILE);
			my $foundGenerPref = 0;
			my $foundMin = 0;
			my $foundMax = 0;
			# print "\nFINISHED THE PROFILE.TXT\n\n";
			open (PREFERENCES, "<$students[$profile_num]/preferences.txt") or die "Cannot open $students[$profile_num]/preferences.txt, $!\n";
			while (my $line = <PREFERENCES>) {
				chomp $line;
				if ($line =~ m/^\s*gender:\s*$/) {
					# print $line,"This is the gender pref line\n";
					$foundGenerPref = 1;
					next;
				}
				if ($line =~ m/^\s*min:\s*$/) {
					# print $line,"This is the min line\n";
					$foundMin = 1;
					next;
				}
				if ($line =~ m/^\s*max:\s*$/) {
					# print $line,"This is the max line\n";
					$foundMax = 1;
					next;
				}
				if ($foundGenerPref and (not defined ${$userData[$tempCount]}{'user_interest_gender'})) {
					# print "THis is the gender pref VALUE line",$line,"\n";
					$line =~ m/^\s*(.+)\s*$/;
					${$userData[$tempCount]}{'user_interest_gender'} = $1;
					next;
				}
				if ($foundMin and (not defined ${$userData[$tempCount]}{'min_age'})) {
					# print "THis is the min age VALUE line",$line,"\n";
					# print "THE VALUE OF foundGenerPref is $foundGenerPref and ${$userData[$tempCount]}{'min_age'}\n";
					$line =~ m/^\s*(.+)\s*$/;
					${$userData[$tempCount]}{'min_age'} = $1;
					next;
				}
				if ($foundMax and (not defined ${$userData[$tempCount]}{'max_age'})) {
					# print "THis is the max age VALUE line",$line,"\n";
					$line =~ m/^\s*(.+)\s*$/;
					${$userData[$tempCount]}{'max_age'} = $1;
					next;
				}
				last if ($foundGenerPref and $foundMin and $foundMax);
			}
			close (PREFERENCES);
			# print "\nFINISHED THE PREFERENCES.TXT\n\n";
			$profile_num++;
			$tempCount++;
		}
		param('browse_index',$profile_num);
		# print Dumper \@userData;
		$template->param(user_data=>\@userData);
		print $template->output();
		# exit (1);
		$rows++;
	}
	print end_html();
}

preserveVariables(); 

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
	} elsif (param('login') eq "Attempt_Unsuccessful") {
		#the user failed at login, will check for faliure details
		if ($login_fail_status eq "UNKNOWN_USERNAME") {
			print h2("Unknown Username");
			open(LOGIN_INPUT,"<login_input.html") or die "Could not open login_input.html, $!\n";
			while (<LOGIN_INPUT>) {
				print;
			}
			close (LOGIN_INPUT);
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

sub preserveVariables {
	my @validVariables = param();
	foreach my $var (@validVariables) {
		print hidden("$var") if ($var ne "password");
	}
}