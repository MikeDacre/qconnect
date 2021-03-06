#! /bin/bash
# make_package.sh
# Copyright (C) 2015 Mike Dacre <mike@dacre.me>
#
# Distributed under terms of the MIT license.
#

if [[ $# < 1 ]]; then
  echo "Please provide version number"
  exit 1
fi

pkgver=$1
pkgname=qconnect
pkgfiles=(qconnect.py qconnect.1.gz README.md LICENSE install.sh)

echo "Creating ${pkgname}_${pkgver}"
mkdir ${pkgname}_${pkgver}
echo $pkgfiles
for i in ${pkgfiles[*]}; do
  echo "Copying $i"
  cp ../$i ${pkgname}_${pkgver}
done

echo "Creating tarball"
tar czf ${pkgname}_${pkgver}.tar.gz ${pkgname}_${pkgver}

rm -rf ${pkgname}_${pkgver}

echo "Signing"
gpg --detach-sign --armour ${pkgname}_${pkgver}.tar.gz

echo "Creating symlinks"
rm ${pkgname}_latest.tar.gz
rm ${pkgname}_latest.tar.gz.asc
ln -s ${pkgname}_${pkgver}.tar.gz ${pkgname}_latest.tar.gz
ln -s ${pkgname}_${pkgver}.tar.gz.asc ${pkgname}_latest.tar.gz.asc
