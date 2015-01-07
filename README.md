qconnect
========
Allows the running of reconnectable applications via torque

Usage
-----

The  default setting is to create and connect to a tmux session, passing '--gui' will create a gui job with xpra. You must provide an executable name, e.g. 'rstudio-bin'.

Passing '--vnc' will create an xfce vnc session and attach to it. You can only have one of these.

If you run without arguments, qconnect will search for a running job, if it cannot find one, it will initiate a tmux job. If there is an existing job, running  it will  connect  to  that  job.  If  there  are multiple jobs present and no arguments are given, qconnect will connect to the first job it finds. If you explicitly request a GUI job, it will connect to the first one of those it finds, if one does not exist, it will create a new one.

By default, qconnect will request 4 cores and 16GB of memory on the node it connects to, these can be modified with the flags '-t' and '-m'. A job name  can  also be specified with '-n'.

Full usage information in the man page


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

