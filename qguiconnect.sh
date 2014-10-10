#! /bin/sh
#
# node_gui_connect.sh
# Copyright (C) 2014 dacre <dacre@fraser-server>
#
# Distributed under terms of the MIT license.
#


qstat=$(qstat -n -1 $1) 
ret=$?
if [[ ! $ret == '0' ]]; then
  exit $ret
fi
node=$(echo $qstat | tail -n 1 | sed 's/.* //g' | sed 's#/.*##g')

echo "Connecting to GUI..."
echo "NOTE: To disconnect without terminating you MUST kill"
echo "this job from the command line"
echo "Closing the window directly will terminate the program"
sleep 2

xpra attach ssh:$USER@$node:$UID
