#!/usr/bin/perl
# 2010/Feb/20 @ Zdenek Styblik 
# zdenek [dot] styblik [snail] gmail [dot] com
# 
# Desc:
# -----
#
# Get all news from AbcLinuxu.cz for past ~7 days from now, 
# transform into text (html2text.py) and e-mail :-)
#
# Patches, comments, improvements - always welcome.
# Trolls - keep it for your self :p
#
# ToDo:
# - I think e-mail encoding is wrong. However, I failed to dig up 
# more and specific info on the subject (= read as "do it exacly 
# like this and not otherwise").
# - ADD articles too
#
# Requires: 
# - Python, html2text.py (patched)
#
# Licence:
# You want my car's licence plate again, or what?
#
# Yo Adrian, I did it! \o/
#
use strict;
use warnings;
use Mail::Sendmail;
use MIME::Base64;

# Settings
my $offset = 0;
my $count = 50;
my $offsetLimit = 2;
my $link = "http://www.abclinuxu.cz/History?type=XXX&from=YYY"
	."&count=ZZZ&orderBy=create&orderDir=desc";
my $mailFrom = 'root@localhost';
my @recipients = qw(root@localhost);

# Main
if ($link !~ /^http[s]?:\/\//) {
	die("URL makes no sense to me.\n");
} # if $link !~ /^http

unless ((-e "html2text.py") && (-x "html2text.py")) {
	die("html2text.py not found or is not executable.\n");
}

my $htmlCollected = '';
my $printOut = '';
# one week later...
my ($sec,$min,$hour,$day,$month,$year,$wday,$yday,$isdst) = 0;
($sec,$min,$hour,$day,$month,$year) = localtime(time-691200);
$month+= 1;
my $dateStop = $day.".".$month.".".$year;

($sec,$min,$hour,$day,$month,$year,$wday,$yday,$isdst) = 
	localtime(time);
$year = 1900 + $year;
my $week = int($yday/7);

while ($offset <= $offsetLimit) {
	my $htmlCollect = 0;
	my $url = $link;
	$url =~ s/XXX/news/;
	$url =~ s/YYY/$offset/;
	$url =~ s/ZZZ/$count/;
	for my $htmlLine (`curl -s '$url'`) {
		chomp($htmlLine);
		$htmlLine =~ s/^\s+//;
		$htmlLine =~ s/\s+$//;
		if ($htmlLine eq "<h1>Archiv zpráviček<\/h1>") {
			$htmlCollect = 1;
#			print "Beginning to collect data\n";
		} # if $lineTmp eq
		if ($htmlCollect == 1 
			&& $htmlLine eq "<form action=\"/History\">") 
		{
#			print "Found stopper\n";
			last;
		} # if $htmlCollect == 1
		if ($htmlCollect == 0) {
			next;
		} # if $htmlCollect
		if ($htmlLine =~ /^<a href=\"\/lide\//) {
			my $tmp = $htmlLine;
			my $cPos = index($tmp, "|");
			$tmp = substr($tmp, $cPos+2, length($tmp));
			$cPos = index($tmp, " ");
			$tmp = substr($tmp, 0, $cPos);
			if ($tmp eq $dateStop) {
#				print "Date stop found\n";
				$offset = 10000;
				last;
			} # if $tmp eq $dateStop
		} # if $htmlLine =~ /^<a
		if ($htmlLine eq "<hr>") {
			$htmlCollected.= $htmlLine."\n";
			$printOut.= `echo '$htmlCollected' | python html2text.py`;
			$htmlCollected = '';
			next;
		} # if $htmlLine eq hr
		$htmlCollected.= $htmlLine."\n";
	} # for my $htmlLine
	$offset++;
} # while $offset =< $offsetLimit

my $mailSubj = "AbcLinuxu zpravicky ".$week."/".$year;
#$mailSubj = '=?UTF-8?B?'.encode_base64($mailSubj, '?=');

my %mail = (
	From    => $mailFrom,
	Subject => $mailSubj,
	'X-Mailer' => "Mail::Sendmail version $Mail::Sendmail::VERSION",
);
$mail{'Content-Type'} = 'text/plain; charset=UTF-8';
$mail{'Content-Transfer-Encoding'} = 'base64';
$mail{'smtp'} = 'localhost';
$mail{'message:'} = $printOut;

for my $recipient (@recipients) {
	$mail{'To:'} = $recipient;
	sendmail(%mail);
} # for my $recipient

#print $printOut."\n";

1;
