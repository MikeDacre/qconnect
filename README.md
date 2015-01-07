qconnect
========
A simple series of scripts that allow you to use
torque and xpra to run persistent GUI programs on 
a cluster.

To use, xpra must be installed on all of the nodes, 
and the users must be able to ssh into the node running
their jobs.

It is possible to make this happen using the pam module
that ships with torque.

Usage
-----

### Starting a job
To use this system, you must start your GUI job using a 
script like the one at /usr/share/torque-xpra/rstudio.pbs

This script runs rstudio on a node with 4GB of memory. It 
starts an xpra server on the node with the same DISPLAY port
as the PBS jobid, this prevents conflicts between jobs.

It also stops the server after the program finishes execution,
this is very important to ensure the health of the nodes. Do
not remove that line.

### Connecting to a job
To connect to the job, just find the job number with qstat 
and run:

    qconnect <job_number>

NOTE:: You must disconnect from the job by killing the 
qconnect session on the command line. Exiting out of the 
window will kill the job and thus the server.

### Getting GUI outputs from a tmux job
If you want to get access to GUI outputs from a qconnect 
tmux session, you can do that by using ``xpra``, for example 
if you wanted to run R:

    export DISPLAY=:$(echo $PBS_JOBID | sed 's#\..*##g')
    xpra start $DISPLAY
    R

Find the node and jobid with:

    qstat -u <user_name> -n -1 | grep int_tmux

Now from a separate window, probably a different ssh session 
to the server run: 

    xpra attach ssh:<user_name>@<node>:<jobid>

Now any gui windows will pop up like normal. They will also be 
preserved. If you Ctrl-C the xpra attach session you won't 
lose any open windows.

When you are done with the GUI app, quit it and then run:

    xpra stop $DISPLAY

It is a little cumbersome, but it is incredibly robust.

This is also the only way to run a stable matlab session. For 
some reason, matlab will not work with the regular ``qconnect -g`` 
flag.


Note on memory usage
--------------------
Note, if you do not use cgroups with torque, you need to be 
careful about memory. Programs like rstudio can have unpredictable 
memory requirements and can stall all other jobs on that node 
if they are not contained.

It is possible to use Docker for this task, but I have not
done that here.

