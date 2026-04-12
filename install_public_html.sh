#!/bin/sh

cd "$(dirname "$0")"

echo "Installing $(realpath ./public_html) to $(realpath ~/public_html)..."
mkdir -p ~/public_html/cgi-bin/
chmod 755 ~/public_html/
chmod 755 ~/public_html/cgi-bin/

rm -rf ~/public_html/ONIDbot
cp -r ./public_html/ONIDbot ~/public_html/ONIDbot

rm -rf ~/public_html/cgi-bin/ONIDbot
cp -r ./public_html/cgi-bin/ONIDbot ~/public_html/cgi-bin/ONIDbot
echo "Done!"

echo ""

echo "Auditing Perms..."
find ./ -type f -perm /g+rwx,o+rwx ! -path "./.git/*" ! -path "./public_html/*" -printf "ERROR mode %m on %p\n"
echo "Done!"