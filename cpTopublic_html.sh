#!/bin/bash
for file in *.cgi
do
	cp $file ../public_html/
	echo "Copied $file to ../public_html/"
	chmod 755 ../public_html/$file
done
