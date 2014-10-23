#!/bin/bash
for file in *.cgi
do
	cp $file ../public_html/
	echo "Copied $file to ../public_html/"
	chmod 755 ../public_html/$file
done
for file in *.html
do
        cp $file ../public_html/
        echo "Copied $file to ../public_html/"
        chmod 666 ../public_html/$file
done
for file in *.css
do
        cp $file ../public_html/
        echo "Copied $file to ../public_html/"
        chmod 666 ../public_html/$file
done

cp -r images ../public_html/
echo "Copied images/ to ../public_html"
