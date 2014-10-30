#!/usr/bin/perl --
use warnings;
use strict;
use CGI qw/:all/;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);
use CGI::Cookie;
warningsToBrowser(1);
use Data::Dumper;
use HTML::Template;
use Storable;

use constant {
	NUM_BROWSE_ROWS => 4,
	BOX_PER_ROW => 4,
	FIELD_LINE => 1,
	FIELD_LINE_LEVEL1 => 2,
	FIELD_LINE_LEVEL2 => 3,
	VALUE_LINE => -1,
	PRIVATE_DATA => ["name","password","courses","email"],
	GENDER_POINTS => 50,
	AGE_POINTS => 10,
	PREFERENCES_POINTS => 5,
	PROFILE_POINTS => 1,
	COURSE_POINTS => 2,
};

my $userDatabase_ref;
my $PRIVATE_DATA = ["name","password","courses","email"];

if (-s 'loveDatabase.hash') {
	#the file already exists
	$userDatabase_ref = retrieve ('loveDatabase.hash');
} else {
	#we have never made the hash.
	$userDatabase_ref = createDatabase ();
	store $userDatabase_ref, 'loveDatabase.hash';
}

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
		exit (0);
	} else {
		my $login_cookie = $cookies{'login_cookie'};
		$login_cookie->value({username => param('username'),login_status => 'LOGGED_IN'},);
		my $profile_counter_cookie = CGI::Cookie->new(-name=>'profile_counter',
									-value => BOX_PER_ROW*NUM_BROWSE_ROWS,
									);
		print "Set-Cookie: $login_cookie\n";
		print "Set-Cookie: $profile_counter_cookie\n";
  		print "Content-Type: text/html\n\n";
  		my $template = HTML::Template->new(filename=>'browse.html');
		print $template->output();
 		$template = HTML::Template->new(filename=>'navbar.html');
		print $template->output();
		$template = HTML::Template->new(filename=>'searchBar.html');
		my %tempHash = $login_cookie->value();
		$template->param(username=>$tempHash{'username'});
		print $template->output();
		$template = HTML::Template->new(filename=>'user_box.tmpl');
		my $counter = 0;
		while ($counter < (BOX_PER_ROW * NUM_BROWSE_ROWS)) {
			my $box_data_ref = generateBoxData("$counter");
			$template->param(user_data=>$box_data_ref);
			print $template->output();
			$counter += BOX_PER_ROW;
		}
		$template = HTML::Template->new(filename=>'navigate.html');
		print $template->output();
		print end_html();
		exit (0);
	}
}

if ((url_param('request') || "") eq "logout") {
	my $login_cookie = $cookies{'login_cookie'};
	$login_cookie->value({username => 'UNSET',login_status => 'LOGGED_OUT'},);
	my $profile_counter_cookie = $cookies{'profile_counter'};
	$profile_counter_cookie->value('0');
	print "Set-Cookie: $login_cookie\n";
	print "Set-Cookie: $profile_counter_cookie\n";
	print "Content-Type: text/html\n\n";
	my $template = HTML::Template->new(filename=>'login.html');
	print $template->output();
	exit (0);
}

if (($ENV{'QUERY_STRING'} || "") eq "") {
	print redirect ('http://cgi.cse.unsw.edu.au/~z5011984/LOVE2041/love2041.cgi?page=browse');
	exit 0;
}

if ((url_param('page') || "") eq "browse") {
	my $profile_counter_cookie = my $profile_counter_cookie = $cookies{'profile_counter'};
	my $counter = $profile_counter_cookie->value();
	my ($counter, $newCounterVal) = findNewVal($counter);
	$profile_counter_cookie->value ("$newCounterVal",);
	print "Set-Cookie: $cookies{'login_cookie'}\n";
	print "Set-Cookie: $profile_counter_cookie\n";
	print "Content-Type: text/html\n\n";
	my $template = HTML::Template->new(filename=>'browse.html');
	print $template->output();
 	$template = HTML::Template->new(filename=>'navbar.html');
	print $template->output();
	if (defined url_param('search_error')) {
		print <<EOF;
		<style>
		::-webkit-input-placeholder { /* WebKit browsers */
    	color:#FF0000;
		}
		</style>
EOF
	}
	$template = HTML::Template->new(filename=>'searchBar.html');
	my $login_cookie = $cookies{'login_cookie'};
	my %tempHash = $login_cookie->value();
	$template->param(username=>"$tempHash{'username'}");
	print $template->output();
	$template = HTML::Template->new(filename=>'user_box.tmpl');
	my $iterator = 0;
	while ($iterator < (BOX_PER_ROW * NUM_BROWSE_ROWS)) {
		my $box_data_ref = generateBoxData("$counter");
		$template->param(user_data=>$box_data_ref);
		print $template->output();
		$counter += BOX_PER_ROW;
		$iterator += BOX_PER_ROW;
	}
	$template = HTML::Template->new(filename=>'navigate.html');
	print $template->output();
	print end_html();
	exit (0);
}

if ((url_param('request') || "") eq "view_profile") {
	if (not defined url_param('user')) {
		print "Status: 400 Bad Request\n";
		print "Content-Type: text/html\n\n";
		print start_html,h1("Bad Request");
		print end_html;
		exit (1);
	}
	printUserProfile (url_param('user'));
}

if (url_param('request') eq "view_matches") {
	print header;
	my $login_cookie = $cookies{'login_cookie'};
	my %hashVal = $login_cookie->value();
	my $template = HTML::Template->new(filename=>'browse.html');
	print $template->output();
 	$template = HTML::Template->new(filename=>'navbar.html');
	print $template->output();
	$template = HTML::Template->new(filename=>'searchBar.html');
	$template->param(username=>$hashVal{'username'});
	print $template->output();
	arrayToUsers(findMatchingUsers($hashVal{'username'}));
	print end_html;
}

if (defined url_param('submit_search')) {
	my $usersArray = getPossibleUsers (url_param('search_username'));
	if (scalar @{$usersArray} == 0) {
		print redirect ('http://cgi.cse.unsw.edu.au/~z5011984/LOVE2041/love2041.cgi?page=browse&search_error=true');
		exit 0;
	} else {
		print header;
		my $template = HTML::Template->new(filename=>'browse.html');
		print $template->output();
 		$template = HTML::Template->new(filename=>'navbar.html');
		print $template->output();
		$template = HTML::Template->new(filename=>'searchBar.html');
		my $login_cookie = $cookies{'login_cookie'};
		my %tempHash = $login_cookie->value();
		$template->param(username=>$tempHash{'username'});
		print $template->output();
		arrayToUsers ($usersArray);
		print end_html;
		exit (0);
	}
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

sub createDatabase {
	my %userDatabase = ();
	my $key1 = undef;
	my $key2 = undef;
	my $lineType;
	my @students = glob ("students/*");
	$userDatabase{'NUM_USERS'} = $#students + 1;
	foreach my $username (@students) {
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
	return \%userDatabase;
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

sub findNewVal {
	my $currentCounter = $_[0];
	if ((url_param('nav') || "") eq "") {
		print h2("in nothing");
		my $newCurrentCounter = $currentCounter - (BOX_PER_ROW * NUM_BROWSE_ROWS);
		$newCurrentCounter = 0 if ($newCurrentCounter < 0);
		my $newCounterVal = $currentCounter;
		return ($newCurrentCounter, $newCounterVal);
	} elsif ((url_param('nav') || "") eq "next") {
		print h2("in next");
		my $newCurrentCounter = $currentCounter;
		my $newCounterVal = $currentCounter + (BOX_PER_ROW * NUM_BROWSE_ROWS);
		$newCounterVal = $newCounterVal - ${$userDatabase_ref}{'NUM_USERS'} if ($newCounterVal > ${$userDatabase_ref}{'NUM_USERS'});
		return ($newCurrentCounter, $newCounterVal);
	} elsif ((url_param('nav') || "") eq "prev") {
		print h2("In prev");
		my $newCurrentCounter = $currentCounter - 2*(BOX_PER_ROW * NUM_BROWSE_ROWS);
		$newCurrentCounter = 0 if (not $newCurrentCounter);
		my $newCounterVal = $currentCounter - (BOX_PER_ROW * NUM_BROWSE_ROWS);
		$newCounterVal = 0 if (not $newCounterVal);
		return ($newCurrentCounter, $newCounterVal);
	}
}

sub printUserProfile {
	my $username = $_[0];
	print header;
	print <<EOF;
<!DOCTYPE html
PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
	<link rel="stylesheet" type="text/css" href="navbar.css">
	<link rel="stylesheet" type="text/css" href="user_styles.css">
	<link rel="stylesheet" type="text/css" href="browse.css">
	<title>$username</title>
</head>
<body>
EOF
	my $template = HTML::Template->new(filename=>'navbar.html');
	print $template->output;
	$template = HTML::Template->new(filename=>'searchBar.html');
	my $login_cookie = $cookies{'login_cookie'};
	my %tempHash = $login_cookie->value();
	$template->param(username=>$tempHash{'username'});
	print $template->output;
	die if (not -d "students/$username");
	print <<EOF;
<p id="p_hack"><img id="profile_pic" src="students/$username/profile.jpg" alt="Profile pic"></p>
<p id="user_name">$username</p>
EOF
print <<EOF;
<div id="about">
	<p>About me</p>
</div>
EOF

my @array_fields = ();
print <<EOF;
<div class="info_container">
	<div id="info_title">
		<p>General Information</p>
	</div>
EOF
my $path = "students/".$username;
foreach my $key (keys %{${$userDatabase_ref}{"students/$username"}{'profile'}}) {
	my $tempKey = $key;
	$key =~ s/_/ /g;
	next if (inPrivateData ($tempKey));
	if (ref (${$userDatabase_ref}{"students/$username"}{'profile'}{$tempKey}) eq "ARRAY") {
		push @array_fields, $tempKey;
		next;
	}
	if (ref (${$userDatabase_ref}{"students/$username"}{'profile'}{$tempKey}) eq "") {
		print <<"		EOF";
		<div id="data">
		<pre>$key : ${$userDatabase_ref}{$path}{profile}{$tempKey}</pre>
		</div>
		EOF
	}
}
print "</div>\n";

foreach my $multiKey (@array_fields) {
	my $tempKey = $multiKey;
	$multiKey =~ s/_/ /g;
	print <<EOF;
<div class="info_container">
	<div id="info_title">
		<p>$multiKey</p>
	</div>
EOF
	my $i = 1;
	while ($i <= $#{${$userDatabase_ref}{$path}{'profile'}{$tempKey}}) {
	print <<"EOF";
<div id="data">
	<pre>$i : ${${$userDatabase_ref}{$path}{profile}{$tempKey}}[$i]</pre>
</div>
EOF
		$i++;
	}
	print "</div>\n";
}

	print <<EOF;
<div id="pref">
	<p>Looking For</p>
</div>
EOF
	print <<EOF;
<div class="info_container">
	<div id="info_title">
		<p>Preferences</p>
	</div>
EOF
	foreach my $key (keys %{${$userDatabase_ref}{"students/$username"}{'preferences'}}) {
		my $tempKey = $key;
		$key =~ s/_/ /g;
		if (ref (${$userDatabase_ref}{"students/$username"}{'preferences'}{$tempKey}) eq "ARRAY") {
			print "<div id=\"data\">";
			print "<pre>$key : ",join(",", @{${$userDatabase_ref}{$path}{'preferences'}{$tempKey}}),"</pre>\n";
			print "</div>\n";
		}
		if (ref (${$userDatabase_ref}{"students/$username"}{'preferences'}{$tempKey}) eq "HASH") {
			print "<div id=\"data\">";
			print "<pre>$key : ","Min->",${$userDatabase_ref}{$path}{'preferences'}{$tempKey}{'min'}," , ",
			"Max->",${$userDatabase_ref}{$path}{'preferences'}{$tempKey}{'max'};
			print "</div>\n";
		}
		if (ref (${$userDatabase_ref}{"students/$username"}{'preferences'}{$tempKey}) eq "") {
			print "<div id=\"data\">";
			print "<pre>$key : ${$userDatabase_ref}{$path}{'preferences'}{$tempKey}</pre>\n";
			print "</div>\n";
		}
	}
	print "</div>";
print end_html;
}

sub inPrivateData {
	my $input = $_[0];
	foreach my $item (@{$PRIVATE_DATA}) {
		return 1 if ($item eq $input);
	}
	return 0;
}

sub arrayToUsers {
	my ($arrayOfUsers_ref) = $_[0];
	# print Dumper $arrayOfUsers_ref;
	my $template = HTML::Template->new(filename=>'user_box.tmpl');
	my $counter = 0;
	my @tempArray;
	my $box_data_ref;
	while ($counter <= $#{$arrayOfUsers_ref}) {
		if ($counter % 4 == 0 and $counter != 0) {
			$box_data_ref = generateBoxData (0,@tempArray);
			# print "<pre>";
			# print Dumper $box_data_ref;
			$template->param(user_data=>$box_data_ref);
			print $template->output();
			@tempArray = ();
		}
		# print "Location of ${$arrayOfUsers_ref}[$counter] is ",  findIndexLocation(${$arrayOfUsers_ref}[$counter]);
		push @tempArray, findIndexLocation(${$arrayOfUsers_ref}[$counter]);
		$counter++;
	}
	if (scalar @tempArray > 0) {
		$counter = 0;
		while ($counter <= 3) {
			if (not defined $tempArray[$counter]) {
				$tempArray[$counter] = -1;
			}
			$counter += 1;
		}
		$box_data_ref = generateBoxData (0, @tempArray);
		# print Dumper $box_data_ref;
		$template->param(user_data=>$box_data_ref);
		print $template->output();
	}
}

sub findIndexLocation {
	my $username = $_[0];
	my @profiles = glob ("students/*");
	my $counter = 0;
	while ($counter <= $#profiles) {
		return $counter if ($username eq $profiles[$counter]);
		$counter++;
	}
	die "profile not found\n";
}

sub generateBoxData {
	my ($startIndex,@indexArray) = @_; 
	my @box_data;
	if (defined $_[1]) {
		my $counter = $startIndex;
		my @profiles = glob ("students/*");
		my $iterator = 0;
		foreach my $index (@indexArray) {
			next if ($index == -1);
			${$box_data[$iterator]}{'user_name'} = ${$userDatabase_ref}{$profiles[$index]}{'profile'}{'username'} || "Unknown";
			${$box_data[$iterator]}{'user_gender'} = ${$userDatabase_ref}{$profiles[$index]}{'profile'}{'gender'} || "Unknown";
			${$box_data[$iterator]}{'user_interest_gender'} = ${$userDatabase_ref}{$profiles[$index]}{'preferences'}{'gender'} || "Unknown";
			${$box_data[$iterator]}{'min_age'} = ${$userDatabase_ref}{$profiles[$index]}{'preferences'}{'age'}{'min'} || "Unknown";
			${$box_data[$iterator]}{'max_age'} = ${$userDatabase_ref}{$profiles[$index]}{'preferences'}{'age'}{'max'} || "Unknown";
			${$box_data[$iterator]}{'image_src'} = "$profiles[$index]/profile.jpg";
			$counter++;
			if ($counter > $#profiles) {
				$counter = 0;
			}
			$iterator++;
		}
	} else {
		my $counter = $startIndex;
		my @profiles = glob ("students/*");
		@box_data = ({},{},{},{});
		my $iterator = 0;
		my $max_interation = BOX_PER_ROW;
		while ($iterator < $max_interation) {
			${$box_data[$iterator]}{'user_name'} = ${$userDatabase_ref}{$profiles[$counter]}{'profile'}{'username'} || "Unknown";
			${$box_data[$iterator]}{'user_gender'} = ${$userDatabase_ref}{$profiles[$counter]}{'profile'}{'gender'} || "Unknown";
			${$box_data[$iterator]}{'user_interest_gender'} = ${$userDatabase_ref}{$profiles[$counter]}{'preferences'}{'gender'} || "Unknown";
			${$box_data[$iterator]}{'min_age'} = ${$userDatabase_ref}{$profiles[$counter]}{'preferences'}{'age'}{'min'} || "Unknown";
			${$box_data[$iterator]}{'max_age'} = ${$userDatabase_ref}{$profiles[$counter]}{'preferences'}{'age'}{'max'} || "Unknown";
			${$box_data[$iterator]}{'image_src'} = "$profiles[$counter]/profile.jpg";
			$counter++;
			if ($counter > $#profiles) {
				$counter = 0;
			}
			$iterator++;
		}
	}
	return \@box_data;
}

sub getPossibleUsers {
	my $searchWord = $_[0];
	my @profiles = glob "students/*";
	my @matches = ();
	foreach my $profile (@profiles) {
		if ($profile =~ m/\Q$searchWord\E/i) {
			push @matches, $profile;
		}
	}
	return \@matches;
}

sub findMatchingUsers {
	my $username = $_[0];
	$username = "students/".$username;
	my %userPoints = ();
	my @finalMatches = ();
	foreach my $user (glob "students/*") {
		# print "The username is $username\nThe student is $user\n";
		next if ($user eq $username);
		foreach my $key (keys %{${$userDatabase_ref}{$username}{'preferences'}}) {
			# print "The key is !!$key!!\n";
			my $sanitisedKey = sanitiseKey ($key);
			# print "The sanitisedKey is $sanitisedKey\n";
			if (ref (${$userDatabase_ref}{$username}{'preferences'}{$key}) eq "") {
				# print "In scalar\n";
				# print "The keyvalue is ${$userDatabase_ref}{$user}{'profile'}{$sanitisedKey}\n";
				if (${$userDatabase_ref}{$user}{'profile'}{$sanitisedKey} eq ${$userDatabase_ref}{$username}{'preferences'}{$key}) {
					$userPoints{$user} += addPoints("preferences",$key);
				}
			} elsif (ref (${$userDatabase_ref}{$username}{'preferences'}{$key}) eq "HASH") {
				# print "In hash\n";
				my $min  = ${$userDatabase_ref}{$username}{'preferences'}{$key}{"min"} || "";
				$min =~ s/[a-zA-Z]//g;
				# print "Min is $min\n";
				my $max = ${$userDatabase_ref}{$username}{'preferences'}{$key}{'max'} || "";
				$max =~ s/[a-zA-Z]//g;
				# print "max is $max\n";
				my $keyValue = ${$userDatabase_ref}{$user}{'profile'}{$sanitisedKey} || "";
				if ($key eq "age") {
					# print "The birthdate is $keyValue\n";
					$keyValue = calculateAge ($keyValue);
					# print "Age is $keyValue\n";
				}
				$keyValue =~ s/[a-zA-Z]//g;
				# print "The keyValue is $keyValue\n";
				if ($keyValue >= $min and $keyValue <= $max) {
					$userPoints{$user} += addPoints ("preferences",$key);
				}
			} elsif (ref (${$userDatabase_ref}{$username}{'preferences'}{$key}) eq "ARRAY") {
				# print "In array\n";
				my $keyValue = ${$userDatabase_ref}{$user}{'profile'}{$sanitisedKey} || "";
				# print "The keyValue is $keyValue\n";
				if (existsInArray ($keyValue,${$userDatabase_ref}{$username}{'preferences'}{$key})) {
					$userPoints{$user} += addPoints ("preferences", $key);
				}
			}
		}
		foreach my $key (keys %{${$userDatabase_ref}{$username}{'profile'}}) {
			next if (not defined ${$userDatabase_ref}{$user}{"profile"}{$key});
			if (ref(${$userDatabase_ref}{$username}{"profile"}{$key}) eq "ARRAY") {
				my $core_array_ref = ${$userDatabase_ref}{$username}{"profile"}{$key};
				foreach my $item (@{$core_array_ref}) {
					if (ref(${$userDatabase_ref}{$user}{"profile"}{$key}) eq "ARRAY") {
						if (existsInArray($item,${$userDatabase_ref}{$user}{"profile"}{$key})) {
							$userPoints{$user} += addPoints ("profile",$key);
						}
					} else {
						if ($item eq ${$userDatabase_ref}{$user}{"profile"}{$key}) {
							$userPoints{$user} += addPoints ("profile",$key);
						}
					}
				}
			} else {
				if (${$userDatabase_ref}{$username}{"profile"}{$key} eq ${$userDatabase_ref}{$user}{"profile"}{$key}) {
					$userPoints{$user} += addPoints ("profile",$key);
				}
			}
		}
	}
	my $counter = 0;
	foreach my $key (sort {$userPoints{$b} <=> $userPoints{$a}} keys %userPoints) {
		push @finalMatches, $key;
		$counter += 1;
		last if ($counter >= 50);
	}
	return \@finalMatches;
}

sub addPoints {
	my ($type,$key) = @_;
	if ($type eq "preferences") {
		return AGE_POINTS if ($key eq "age");
		return GENDER_POINTS if ($key eq "gender");
		return PREFERENCES_POINTS;
	} elsif ($type eq "profile") {
		return COURSE_POINTS if ($key eq "courses");
		return PROFILE_POINTS;
	}
}

sub existsInArray {
	my ($value, $array_ref) = @_;
	foreach my $item (@{$array_ref}) {
		return 1 if ($item eq $value);
	}
	return 0;
}

sub sanitiseKey {
	my $key = $_[0];
	if ($key eq "hair_colours") {
		return "hair_colour";
	} elsif ($key eq "age") {
		return 'birthdate';
	} else {
		return $key;
	}
}

sub calculateAge {
	my $birthday = $_[0];
	my ($day, $month, $year);
	if ($birthday =~ m/([0-9]{4})\/([0-9]{2})\/([0-9]{2})/) {
		($day, $month, $year) = ($3,$2,$1);
	} elsif ($birthday =~ m/([0-9]{2})\/([0-9]{2})\/([0-9]{4})/) {
		($day, $month, $year) = ($1,$2,$3);
	}
	my ($c_day, $c_month, $c_year) = (localtime)[3..5];
	$c_month += 1;
	$c_year += 1900;
	my $age = $c_year - $year;
	if (($month >= $c_month and $day >= $c_day) or $month > $c_month) {
		$age++;
	}
	return $age;
}