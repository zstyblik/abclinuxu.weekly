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
use Time::Local;
use LWP;

# Settings
my $count = 50;
my $debug = 0;
my $link = "http://www.abclinuxu.cz/History?type=XXX&from=YYY"
	."&count=ZZZ&orderBy=create&orderDir=desc";
my $offset = 0;
my $offsetLimit = 2;
## mail
my $mailFrom = 'root@localhost';
my @recipients = qw(joe@localhost);

# desc: find time in HTML line in Articles section
# $textLine: string;
# @return: string;
sub getTimeArticles {
	my $textLine = shift;
	$textLine =~ s/^\s+//g;
	$textLine =~ s/\s+$//g;
	my @chunks = split(' ', $textLine);
	return undef unless ($chunks[0] =~ /[0-9]+/);
	return $chunks[0];
}
# desc: find time in HTML line in News section
# $textLine: string;
# @return: string;
sub getTimeNews {
	my $textLine = shift;
	my $cPos = index($textLine, "|");
	my $datePart = substr($textLine, $cPos+2, length($textLine));
	$cPos = index($datePart, " ");
	my $dateFound = substr($datePart, 0, $cPos);
	return undef unless ($dateFound =~ /[0-9]+/);
	return $dateFound;
}
# desc: print help
sub printHelp {
	print "Get digest of ABCLinuxu's articles/news for week.\n\n";
	print "Parameters are:\n";
	print "\t-a\tfetch and mail articles (can't be used with -n)\n";
	print "\t-h\tprint this help\n";
	print "\t-n\tfetch and mail news (can't be used with -a)\n";
	exit 1;
}

### Main ###
if ($link !~ /^http[s]?:\/\//) {
	die("URL makes no sense to me.\n");
} # if $link !~ /^http

unless ((-e "./html2text.py") && (-x "./html2text.py")) {
        die("html2text.py not found or is not executable.\n");
}

my $numArgs = $#ARGV + 1;
if ($numArgs == 0 || $numArgs > 1) {
	&printHelp;
}


my $toFetch = 'nic';
my $collectStart = 'nikde';
my $fetchType = 'zadny';
my $dateNeedle = 'zadna';

while (1) {
	if ($ARGV[0] eq '-a') {
		$toFetch = 'articles';
		$collectStart = 'článků';
		$fetchType = 'clanky';
		$dateNeedle = 'autori';
		last;
	}
	if ($ARGV[0] eq '-n') {
		$toFetch = 'news';
		$collectStart = 'zpráviček';
		$fetchType = 'zpravicky';
		$dateNeedle = 'lide';
		last;
	}
	&printHelp;
}

my $browser = LWP::UserAgent->new;
my $dateLine = 0; # 0/1 internal control
my $dateStop = time-691200; # -1 week
my $htmlCollected = '';
my $printOut = '';

while ($offset <= $offsetLimit) {
	my $htmlCollect = 0;
	my $url = $link;
	$url =~ s/XXX/$toFetch/;
	$url =~ s/YYY/$offset/;
	$url =~ s/ZZZ/$count/;
	print $url."\n" if ($debug == 1);
	my $response = $browser->get( $url ) 
		or die("Unable to get URL '$url'.");
	for my $htmlLine ( split(/\n/, $response->content) ) {
		chomp($htmlLine);
		$htmlLine =~ s/^\s+//;
		$htmlLine =~ s/\s+$//;
		if ($htmlLine eq "<h1>Archiv $collectStart<\/h1>") {
			$htmlCollect = 1;
			print "Beginning to collect data\n" if ($debug == 1);
		} # if $lineTmp eq
		if ($htmlCollect == 1 
			&& $htmlLine eq "<form action=\"/History\">") 
		{
			print "Found stopper\n" if ($debug == 1);
			$offset = 99999;
			last;
		} # if $htmlCollect == 1
		if ($htmlCollect == 0) {
			next;
		} # if $htmlCollect

		if ($htmlLine eq '<p class="meta-vypis">') {
			print "Pre-date\n" if ($debug == 1);
			$dateLine = 1;
		}
		if ($dateLine == 1 && $htmlLine eq '</p>') {
			$dateLine = 0;
		}
		if ($dateLine == 1 
			&& $htmlLine =~ /[0-9]+\.[0-9]+\.[0-9]+ [0-9]+:[0-9]+/) {
			my $tmp;
			if ($toFetch eq 'articles') {
				$tmp = &getTimeArticles($htmlLine);
			} else {
				$tmp = &getTimeNews($htmlLine);
			}
			$dateLine = 0 unless ($tmp);
			next unless ($tmp && $tmp =~ /[0-9]+/);
			print $tmp."\n" if ($debug == 1);
			my @f_date = split(/\./, $tmp);
			my $f_time = timelocal(0, 0, 12, $f_date[0], $f_date[1] - 1, 
				$f_date[2] - 1900);
			print $f_time." X ".$dateStop."\n" if ($debug == 1);
			if ($f_time < $dateStop) {
				print "Date stop found\n" if ($debug == 1);
				$offset = 10000;
				last;
			} # if $tmp < $dateStop
		} # if $dateLine == 1 ...
		if ($htmlLine eq "<hr>") {
			$htmlCollected.= $htmlLine."\n";
			$printOut.= `echo '$htmlCollected' | ./html2text.py`;
			$htmlCollected = '';
			next;
		} # if $htmlLine eq hr
		$htmlCollected.= $htmlLine."\n";
	} # for my $htmlLine
	$offset++;
} # while $offset =< $offsetLimit

my ($sec,$min,$hour,$day,$month,$year,$wday,$yday,$isdst) = 
	localtime(time);
$year = 1900 + $year;
my $week = int($yday/7);

my $mailSubj = "AbcLinuxu ".$fetchType." ".$week."/".$year;
#$mailSubj = '=?UTF-8?B?'.encode_base64($mailSubj, '?=');

my %mail = (
	From    => $mailFrom,
	Subject => $mailSubj,
	'X-Mailer' => "Mail::Sendmail version $Mail::Sendmail::VERSION",
);
$mail{'Content-Type'} = 'text/plain; charset=UTF-8';
#$mail{'Content-Transfer-Encoding'} = 'base64';
$mail{'Content-Transfer-Encoding'} = 'quoted-printable';
$mail{'smtp'} = 'localhost';
$mail{'message:'} = $printOut;

for my $recipient (@recipients) {
	$mail{'To:'} = $recipient;
	sendmail(%mail);
} # for my $recipient

