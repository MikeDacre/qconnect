#! /bin/sh
# make_package.sh
# Copyright (C) 2015 Mike Dacre <mike@dacre.me>
#
# Distributed under terms of the MIT license.
#

pkgver=$1
pkgname=qconnect
pkgfiles=(qconnect.py qconnect.1.gz README.md LICENSE)

mkdir ${pkgname}_${pkgver}
for i in $pkgfiles; do
  cp ../$i ${pkgname}_${pkgver}
done

tar czf ${pkgname}_${pkgver}.tar.gz ${pkgname}_${pkgver}

rm -rf ${pkgname}_${pkgver}

gpg --detach-sign ${pkgname}_${pkgver}.tar.gz
