#!/usr/bin/perl --
use warnings;
use strict;
use CGI qw/:all/;
use CGI::Carp qw(fatalsToBrowser warningsToBrowser);
use CGI::Cookie;
warningsToBrowser(1);
use Data::Dumper;
use HTML::Template;
use File::Basename; #a module that splits file paths into a path, name and a suffix
use Storable; #this module is used to store any data structure in a file
#I use it to simulate database creation

#the main structure of the program is multiple if statements dealing with different requests.
#each if block is self contained, and has an exit at the end.
#This means that only one block will run per call of the program

use constant {
	NUM_BROWSE_ROWS => 4,
	BOX_PER_ROW => 4,
	FIELD_LINE => 1,
	FIELD_LINE_LEVEL1 => 2,
	FIELD_LINE_LEVEL2 => 3,
	VALUE_LINE => -1,
	GENDER_POINTS => 100,
	AGE_POINTS => 50,
	PREFERENCES_POINTS => 5,
	PROFILE_POINTS => 1,
	COURSE_POINTS => 2,
};

my $userDatabase_ref; #the global variable for the user database. It will contain a hash ref
my $PRIVATE_DATA = ["name","password","courses","email"]; #this is data that should not be printed
my $SKIP_DATA = ["gender","email","password","username","name"]; #this is data that should be skipped during matching

#store and retrieve are both part of the storable module
#if a databse has not been made yet, we make one. Else we retrieve from it
if (-s 'loveDatabase.hash') {
	#the file already exists
	$userDatabase_ref = retrieve ('loveDatabase.hash');
} else {
	#we have never made the hash.
	$userDatabase_ref = createDatabase ();
	store $userDatabase_ref, 'loveDatabase.hash';
}

#this checks if the program was called from an email link (password recovery)
#however this is also run when the user tries to change his password while logged in (using a redirection header)
if ((url_param('src') || "") eq "email") {
	if ((url_param('request') || "") eq "changePassword") {
		if (defined param('change_pass_submit')) {
			#if the student has sent a request for password change
				my $oldPass = param('old_password');
				my $newPass = param('new_password');
				my $username = url_param('user') || die "Cannot find temp\n";
				if ($oldPass ne ${$userDatabase_ref}{"students/$username"}{'profile'}{'password'}) {
					#incorrect password was entered
					print header;
					my $template = HTML::Template->new(filename=>'recoverPassword.html');
					#providing necessary error information into the template
					$template->param(ERROR=>'1',old_pass=>'1',change_pass=>'1',uname_src=>"$username");
					print $template->output();
				} else {
					${$userDatabase_ref}{"students/$username"}{'profile'}{'password'} = $newPass;
					changePassword($username,$oldPass,$newPass);
					my $tempHash = createDatabase();
					store $tempHash, 'loveDatabase.hash';
					print header,start_html(-head=>[
							Link ({-rel=>'stylesheet',-href=>'navbar.css',-type=>'text/css'}),
						],
					-title=>'Success');
					print h1({-style=>'text-align:center'},"Successfully changed password");
					print a({-href=>"love2041.cgi",
							 -style=>'margin-left:45%;'},"Back to login");
					print end_html;
				}
		} else {
			#display the default page
			my $username = url_param('user') || die "User not provided\n";
			print header;
			my $template = HTML::Template->new(filename=>'recoverPassword.html');
			$template->param(change_pass=>'1',uname_src=>"$username");
			print $template->output();
		}
	}
	exit (0);
}

#we make a global cookies hash, and fetch any cookies previously made
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
		and (not defined param('login_submit') and (url_param('request') ne "forgot_password"))) {
		my $template = HTML::Template->new(filename=>'login.html');
		print header;
		print $template->output();
		exit (0);
	}
}

if ((url_param('request') || "") eq "forgot_password") {
	print header;
	my $template = HTML::Template->new(filename=>'recoverPassword.html');
	if (defined param('recovery_submit')) {
		my $username = param('recovery_uname');
		if (defined ${$userDatabase_ref}{"students/$username"}) {
			$template->param(correct_uname=>'1');
			print $template->output;
			my $password = 'adiswa123@gmail.com';#${$userDatabase_ref}{"students/$username"}{'profile'}{"password"};
			my $message = <<EOF;
<html>
<h3>Hello $username</h3>
Your password is \'$password\'
If you wish to change this, please follow the link below
<a href=http://cgi.cse.unsw.edu.au/~z5011984/LOVE2041/love2041.cgi?src=email&request=changePassword&user=$username><pre>Click to change password</pre></a>
</html>
EOF
			my $from = 'doNotReply@love2041.com';
			my $to = ${$userDatabase_ref}{"students/$username"}{'profile'}{'email'};
			my $subject = 'Password Recovery';
			sendHtmlMail($from,$to,$subject,$message); #uses the unix sendmail program
		} else {
			$template->param(ERROR=>'1',Uname=>'1',validate_uname=>'1');
			print $template->output();
		}
	} else {
		$template->param(validate_uname=>'1');
		print $template->output();
	}
	exit (0);
}

if (defined param('login_submit')) {
#if user has send a login request
	my $validation_code = validateLogin(param('username'),param('password'));
	#there are validation codes for different cases
	#the fucntion determineStatus() takes in the code and gives out a status
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

#AT THIS POINT IN THE PROGRAM, ALL CASES FOR LOGGED OUT USERS IS TAKEN CARE OF
#NO USER CAN BE LOGGED OUT AFTER THIS POINT

#to account for the case of the user tries to go to the main website after they are logged in
if (($ENV{'QUERY_STRING'} || "") eq "") {
	print redirect ('love2041.cgi?page=browse');
	exit 0;
}

if ((url_param('page') || "") eq "browse") {
	my $profile_counter_cookie = my $profile_counter_cookie = $cookies{'profile_counter'};
	my $counter = $profile_counter_cookie->value();
	my ($counter, $newCounterVal) = findNewVal($counter);
	#the profile counter cookies is used to keep track of what profiles were showing
	$profile_counter_cookie->value ("$newCounterVal",);
	print "Set-Cookie: $cookies{'login_cookie'}\n";
	print "Set-Cookie: $profile_counter_cookie\n";
	print "Content-Type: text/html\n\n";
	my $template = HTML::Template->new(filename=>'browse.html');
	print $template->output();
 	$template = HTML::Template->new(filename=>'navbar.html');
	print $template->output();
	#if the search was unsuccessful last time, the placeholder for the searchbar is made red
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

#if the user wants to view an indiviual profile
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
	#the arrayToUsers function takes in an array of users
	#and displayes the user box model.

	#the findMatchingUsers function takes in a username,
	#and returns an array of usernames containing the top 50 matches
	arrayToUsers(findMatchingUsers($hashVal{'username'}));
	print end_html;
}

if (defined url_param('submit_search')) {
	my $usersArray = getPossibleUsers (url_param('search_username'));
	if (scalar @{$usersArray} == 0) {
		print redirect ('love2041.cgi?page=browse&search_error=true');
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

#if it is an account management request
if ((url_param('request') || "") eq "view_account") {
	if (not defined url_param('page') or url_param('page') eq "acc_info") {
		#if page not provided, go to account info page
		print header;
		my $template = HTML::Template->new(filename=>'manageAccount.html');
		$template->param(acc_info=>'1',username=>getCurrentUsername());
		print $template->output();
	}
	if(url_param('page') eq "edit_profile") {
		#if edit profile is requested, we display a page in which the user can edit their profile description
		if (not defined param('prof_data_submit')){
			my $profile_text = userProfileText (getCurrentUsername(),"read");
			print header;
			my $template = HTML::Template->new(filename=>'manageAccount.html');
			$template->param(edit_profile=>'1',profile_text=>"$profile_text");
			print $template->output();
		} else {
			my $profile_text = param('input_text');
			userProfileText(getCurrentUsername(),"write",$profile_text);
			$profile_text = userProfileText (getCurrentUsername(),"read");
			print header;
			my $template = HTML::Template->new(filename=>'manageAccount.html');
			$template->param(edit_profile=>'1',profile_text=>"$profile_text");
			print $template->output();
		}
	} elsif ((url_param('page') || "") eq "manage_pic") {
		#if the request is for picture management
		if (defined param('image_delete')) {
			#if a delete request is sent
			my $image_source = param('image_source');
			die "Source not found\n" if (not defined $image_source);
			`rm $image_source`;
			print redirect ("love2041.cgi?request=view_account&page=manage_pic");
			exit (0);
		}
		if (defined param('submit_upload')) {
			#we get the file path sent by the browser
			my $filepath = param('img_upload');
			#if the filepath is undef, there was an error uploading
			if (not defined $filepath) {
				print header,start_html,h2("Upload Corrupted");
				print a({-href=>'love2041.cgi?request=view_account&page=manage_pic'},"Go back");
				print end_html;
				exit (1);
			}
			#the fileparse function breakes up the path
			my ($name,$path,$suffix) = fileparse ($filepath, '..*');
			my $filename = "$name"."$suffix"; #we only need the literal filename
			my $username = getCurrentUsername();
			my $fileHandle = upload("img_upload");
			open (UPLOAD_FILE,">students/$username/$filename") or die "Could not create file";
			binmode UPLOAD_FILE;
			while (<$fileHandle>) {
				print UPLOAD_FILE;
			}
			close (UPLOAD_FILE);
			print redirect ("love2041.cgi?request=view_account&page=manage_pic");
			exit (0);
		}
		my $template = HTML::Template->new(filename=>'manageAccount.html');
		my $picsStructure = [];
		my $user = getCurrentUsername();
		#picsStructure is an array of hash references
		#This is the data structure that needs to be passed in to the template loop
		foreach my $image_src (glob "students/$user/*.jpg") {
			my $tempHash = {};
			${$tempHash}{'image_path'} = $image_src;
			push @{$picsStructure},$tempHash;
		}
		$template->param(manage_pic=>'1',image_loop=>$picsStructure);
		print header;
		print $template->output();
	} elsif ((url_param('page') || "") eq "change_pass") {
		print redirect ("love2041.cgi?src=email&request=changePassword&user=".getCurrentUsername());
	}
	exit (0);
}


#validates login info, has various return statuses for debugging
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

#translates error status codes from validateLogin into strings
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

#this function parses the user data and creates a hash with all the data stored in it
#the function returns a reference to this hash
sub createDatabase {
	my %userDatabase = ();
	my $key1 = undef; #key1 will contain a value line with 1 indent
	my $key2 = undef; #key2 will contain a value line with 2 indents
	my $lineType; #will store the line type
	#the line type is defined my FIELD_LINE_LEVEL1 or FIELD_LINE_LEVEL2
	#FIELD_LINE_LEVEL_1 is a line with no indent
	#FIELD_LINE_LEVEL_2 is a line with 1 tab indent
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
							#if we see a field line, and our key1 is defined, it means that we have reached the end of that field
							#and are now startig the next
							#therefore both key1 and key2 are set to undef
							#the next over here acts as a redo, since the counter is incremented manually
							$key1 = undef;
							$key2 = undef;
							next;
						}
						$key1 = extractData ($line, $lineType);
					} else {
						$key2 = extractData ($line, $lineType);
					}
				} else {
					#in this part, we check if the value of the hash at that point is an array, a scalar or undef

					#if it is unef we simply assign to that place, since we have not been there before

					#if it is a scalar, it means that that field must now contain more than 1 value
					#hence we make an array reference, and store the values in that

					#if it is already an array reference, we simply push on to it
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
	return \%userDatabase;
}

#helper function for createDatabase
#checks the line indent and returns a value accordingly
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

#helper function for createDatabase
#extracts the data from a value line
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

#this function returns counter values.
#the first reutrn is for the starting counter for the profiles to be displayed in browse
#the second value is the one to be printed to the profile_counter_cookie
sub findNewVal {
	my $currentCounter = $_[0];
	if ((url_param('nav') || "") eq "") {
		#we don't move
		my $baseCounter = $currentCounter - (BOX_PER_ROW * NUM_BROWSE_ROWS);
		return ($baseCounter, $currentCounter);
	} elsif ((url_param('nav') || "") eq "next") {
		#make sure not to overstep
		if ($currentCounter + (BOX_PER_ROW * NUM_BROWSE_ROWS) >= ${$userDatabase_ref}{"NUM_USERS"}) {
			$currentCounter = ${$userDatabase_ref}{"NUM_USERS"};
		} else {
			$currentCounter += (BOX_PER_ROW * NUM_BROWSE_ROWS);
		}
		my $baseCounter = $currentCounter - (BOX_PER_ROW * NUM_BROWSE_ROWS);
		return ($baseCounter, $currentCounter);
	} elsif ((url_param('nav') || "") eq "prev") {
		#don't go below - MAX_USERS
		if ($currentCounter - (BOX_PER_ROW * NUM_BROWSE_ROWS) <= -(${$userDatabase_ref}{"NUM_USERS"})) {
			$currentCounter = -(${$userDatabase_ref}{"NUM_USERS"}) + (BOX_PER_ROW * NUM_BROWSE_ROWS);
		} else {
			$currentCounter -= (BOX_PER_ROW * NUM_BROWSE_ROWS);
		}
		my $baseCounter = $currentCounter - (BOX_PER_ROW * NUM_BROWSE_ROWS);
		return ($baseCounter, $currentCounter);
	}
}

#this function takes in a username and prints the profile page
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
	#setting up the basic templates, printing the top parts of the page
	my $template = HTML::Template->new(filename=>'navbar.html');
	print $template->output;
	$template = HTML::Template->new(filename=>'searchBar.html');
	$template->param(username=>getCurrentUsername());
	print $template->output;
	die if (not -d "students/$username");
	my $personalText = userProfileText($username,"read");
	print <<EOF;
<p id="p_hack"><img id="profile_pic" src="students/$username/profile.jpg" alt="Profile pic"></p>
<p id="user_name">$username</p>
EOF
	print <<EOF;
<div id="about">
	<p id="me">About me</p>
	<p id="prof_text">$personalText</p>
</div>
EOF
	print <<EOF;
<div class="info_container">
	<div id="info_title">
		<p>General Information</p>
	</div>
EOF
	my @array_fields = (); #this will store all the fields that have multiple values
	#these fields will be printed in separate boxes
	my $path = "students/".$username;
	#this loop prints only the single value fields in one box
	foreach my $key (keys %{${$userDatabase_ref}{"students/$username"}{'profile'}}) {
		my $tempKey = $key;
		$key =~ s/_/ /g;
		next if (inPrivateData ($tempKey));
		if (ref (${$userDatabase_ref}{"students/$username"}{'profile'}{$tempKey}) eq "ARRAY") {
			#multiple value fields are stored in an array
			push @array_fields, $tempKey;
			next;
		}
		if (ref (${$userDatabase_ref}{"students/$username"}{'profile'}{$tempKey}) eq "") {
			if ($tempKey eq "birthdate") {
				my $age = calculateAge(${$userDatabase_ref}{$path}{profile}{$tempKey});
				print <<"EOF";
<div id="data">
	<pre>Age : $age</pre>
</div>
EOF
			}
			print <<"EOF";
<div id="data">
	<pre>$key : ${$userDatabase_ref}{$path}{profile}{$tempKey}</pre>
</div>
EOF
		}
	}

	print "</div>\n";

	#now we print the different boxes for the multiple value fields
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
	#we now print the preferences
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
	print <<EOF;
<div id=about>
	<p>Pictures of me</p>
</div>
EOF
	#this loop prints any other image files in the directory.
	foreach my $image_src (glob "students/$username/*.jpg") {
		print "<img style=\'margin-right:2em;\' src=$image_src alt=Picture>\n";
	} 
	print end_html;
}

#a function to check if a value is in the private data array
sub inPrivateData {
	my $input = $_[0];
	foreach my $item (@{$PRIVATE_DATA}) {
		return 1 if ($item eq $input);
	}
	return 0;
}

#this function takes in a list of users, and prints a box for each user
#this function is essentially a filter, that makes sets of 4 from the list
#and gives index locations for each of those 4 users to the function generateBoxData, which prints the boxes
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
			$template->param(user_data=>$box_data_ref);
			print $template->output();
			@tempArray = ();
		}
		push @tempArray, findIndexLocation(${$arrayOfUsers_ref}[$counter]);
		$counter++;
	}
	#if after coming out of this loop we still have users in the array
	#that means number of users % 4 != 0.
	#the rest of the spots are filled with -1
	if (scalar @tempArray > 0) {
		$counter = 0;
		while ($counter <= 3) {
			if (not defined $tempArray[$counter]) {
				$tempArray[$counter] = -1;
			}
			$counter += 1;
		}
		$box_data_ref = generateBoxData (0, @tempArray);
		$template->param(user_data=>$box_data_ref);
		print $template->output();
	}
}

#given a user, this function finds the index of that user in the standard array given by glob
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

#This function has been split into two major parts (two ways of calling the function)
#One way of calling it is with a counter value.
#The other way of calling the function is giving it an array of indexes as its second argument

#In both cases, the function generates an array of hash references, which is the data structure that needs
#to be passed into the html template loop.
sub generateBoxData {
	my ($startIndex,@indexArray) = @_;
	my @box_data;
	if (defined $_[1]) {
		#the case where we have an array of indexes
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
			my $birthdate = ${$userDatabase_ref}{$profiles[$index]}{'profile'}{'birthdate'};
			if (defined $birthdate) {
				${$box_data[$iterator]}{'user_age'} = calculateAge ($birthdate);
			} else {
				${$box_data[$iterator]}{'user_age'} = "UNKNOWN";
			}
			${$box_data[$iterator]}{'image_src'} = "$profiles[$index]/profile.jpg";
			$counter++;
			if ($counter > $#profiles) {
				$counter = 0;
			}
			$iterator++;
		}
	} else {
		#here we are only given 1 counter
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
			my $birthdate = ${$userDatabase_ref}{$profiles[$counter]}{'profile'}{'birthdate'};
			if (defined $birthdate) {
				${$box_data[$iterator]}{'user_age'} = calculateAge ($birthdate);
			} else {
				${$box_data[$iterator]}{'user_age'} = "UNKNOWN";
			}
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

#This is a matching helper function
#Given a search term it attepmts to match this term to each of the user names
#Returns an array of each matched
sub getPossibleUsers {
	my $searchWord = $_[0];
	my @profiles = glob "students/*";
	my @matches = ();
	foreach my $profile (@profiles) {
		if ($profile =~ m/students\/.*\Q$searchWord\E.*/i) {
			push @matches, $profile;
		}
	}
	return \@matches;
}

#this function does the following
# given a username, it goes through all other users and asssigns points to each user.
# based on the number of things the other user matches.
# It then takes the top 50 of these users and returns an array reference.
sub findMatchingUsers {
	my $username = $_[0];
	$username = "students/".$username;
	my %userPoints = ();
	my @finalMatches = ();
	#please note that $username refers to the logged in user (the one we are matching for)
	#And that $user refers to the current user we are checking

	#the matching here also checks for the type of structure present at the place in the hash
	#and deals with it accordingly, e.g. finds max and min if there is a hash reference.
	foreach my $user (glob "students/*") {
		next if ($user eq $username); #we don't want to match the same user

		#this foreach loop goes through and matches $username preferences to $user profile
		foreach my $key (keys %{${$userDatabase_ref}{$username}{'preferences'}}) {
			my $sanitisedKey = sanitiseKey ($key); #go to the sanitiseKey function for a description
			if (ref (${$userDatabase_ref}{$username}{'preferences'}{$key}) eq "") {
				if (${$userDatabase_ref}{$user}{'profile'}{$sanitisedKey} eq ${$userDatabase_ref}{$username}{'preferences'}{$key}) {
					$userPoints{$user} += addPoints("preferences",$key); #go to addPoints function for a description
				}
			} elsif (ref (${$userDatabase_ref}{$username}{'preferences'}{$key}) eq "HASH") {
				my $min  = ${$userDatabase_ref}{$username}{'preferences'}{$key}{"min"} || "0";
				$min =~ s/[a-zA-Z]//g;
				my $max = ${$userDatabase_ref}{$username}{'preferences'}{$key}{'max'} || "0";
				$max =~ s/[a-zA-Z]//g;
				my $keyValue = ${$userDatabase_ref}{$user}{'profile'}{$sanitisedKey} || "0";
				if ($key eq "age") {
					$keyValue = calculateAge ($keyValue);
				}
				$keyValue =~ s/[a-zA-Z]//g;
				if ($keyValue >= $min and $keyValue <= $max) {
					$userPoints{$user} += addPoints ("preferences",$key);
				}
			} elsif (ref (${$userDatabase_ref}{$username}{'preferences'}{$key}) eq "ARRAY") {
				my $keyValue = ${$userDatabase_ref}{$user}{'profile'}{$sanitisedKey} || "";
				if (existsInArray ($keyValue,${$userDatabase_ref}{$username}{'preferences'}{$key})) {
					$userPoints{$user} += addPoints ("preferences", $key);
				}
			}
		}

		#this foreach loop matches the profiles of both users being compared
		foreach my $key (keys %{${$userDatabase_ref}{$username}{'profile'}}) {
			next if (not defined ${$userDatabase_ref}{$user}{"profile"}{$key});
			next if (existsInArray($key, $SKIP_DATA));
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

	#we now get the top 50 users (by points)
	foreach my $key (sort {$userPoints{$b} <=> $userPoints{$a}} keys %userPoints) {
		push @finalMatches, $key;
		$counter += 1;
		last if ($counter >= 50);
	}
	return \@finalMatches;
}


#based on the input, the fuction returns the correct number of points to be added
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

#given a value and an array reference, the funciton checks for the value inside the array
sub existsInArray {
	my ($value, $array_ref) = @_;
	foreach my $item (@{$array_ref}) {
		return 1 if ($item eq $value);
	}
	return 0;
}

#in some cases, the key in the preferences hash differs to its corresponding value in the profile hash
#example in preferences its age , and profile is birthdate.
#the sanitiseKey function changes the base key to its corresponding value for the profile.
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

#function assumes the input is in the following formats
# DD/MM/YYYY or YYYY/MM/DD
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
	if ((int($c_month) <= $month and int($c_day) < $day) or (int($c_month) < $month)) {
		$age--;
	}
	return $age;
}

#uses the unix sendmail utility to send a html mail
#usage: sendmail ($from, $to, $subject,$message)
sub sendHtmlMail {
	my ($from, $to, $subject,$message) = @_;
	open(MAIL, "|/usr/sbin/sendmail -t") or die "Cannot use sendmail, $!\n";
	print MAIL "To: $to\n";
	print MAIL "From: $from\n";
	print MAIL "Subject: $subject\n";
	print MAIL "Content-Type: text/html\n\n";
	print MAIL $message;
	close (MAIL);
}

#changes the password in the users file.
sub changePassword {
	my ($username,$oldPass,$newPass) = @_;
	open (PROFILE, "<students/$username/profile.txt") || die "Cannot open students/$username/profile.txt,$!\n";
	my $found = 0;
	my @input = <PROFILE>;
	foreach my $line (@input) {
		if ($line =~ m/\s*password:\s*$/) {
			$found = 1;
			next;
		}
		if ($found == 1) {
			$line =~ s/\Q$oldPass\E/$newPass/;
			last;
		}
	}
	close (PROFILE);
	open (PROFILE,">students/$username/profile.txt");
	my $out = join("",@input);
	print PROFILE $out;
	close (PROFILE);
}

#Usage 1 : userProfileText ($username,"read");
# This usage opens the profile text for the given user, and returns the text present
# if no text exists, "" is returned.

#usage 2 : userProfileText($username,"write",$textToWrite);
# This usage opens the profile text file for the given user, and writes the given text to the file
sub userProfileText {
	my $username = $_[0];
	my $mode = $_[1];
	my $textToWrite = $_[2];
	if ($mode eq "write" and (not defined $textToWrite)) {
		die "Invalid call of function userProfileText, please provide text to write\n";
	}
	if ($mode eq "read") {
		if  (not(-e "students/$username/prof_text.txt")) {
			open (FILE, ">students/$username/prof_text.txt");
			print FILE "";
			close (FILE);
			chmod oct("0644"), "students/$username/prof_text.txt";
		}
		open (TEXT, "<students/$username/prof_text.txt") or die "Cannot open students/$username/prof_text.txt, $!\n";
		my @input = <TEXT>;
		my $returnVal = join ("", @input);
		return $returnVal || "";
	} elsif ($mode eq "write") {
		open (FILE, ">students/$username/prof_text.txt") or die "cannot open students/$username/prof_text.txt,$!\n";
		print FILE $textToWrite;
		close (FILE);
	}
}

#gets logged in user from the login_cookie
sub getCurrentUsername {
	my $login_cookie = $cookies{'login_cookie'};
	my %tempHash = $login_cookie->value();
	my $user = $tempHash{'username'};
	return $user;
}
