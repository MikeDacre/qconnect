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

Installation
------------
You can find the latest package [here](https://github.com/MikeDacre/qconnect/blob/master/packages/qconnect_latest.tar.gz)
and the GPG signature [here](https://github.com/MikeDacre/qconnect/blob/master/packages/qconnect_latest.tar.gz)

To install, simply unpack the archive, and put qconnect.py somewhere
in your ``$PATH``. 

NOTE: Right now it is only compatible with linux.

You can also put qconnect.1.gz into your man path if you wish.

If you are on arch linux, I have an installation package
available on the [aur](https://aur.archlinux.org/packages/qconnect/)

Usage
-----

### Starting a job ###
To use this system, you must start your GUI job using a 
script like the one at /usr/share/torque-xpra/rstudio.pbs

This script runs rstudio on a node with 4GB of memory. It 
starts an xpra server on the node with the same DISPLAY port
as the PBS jobid, this prevents conflicts between jobs.

It also stops the server after the program finishes execution,
this is very important to ensure the health of the nodes. Do
not remove that line.

### Connecting to a job ###
To connect to the job, just find the job number with qstat 
and run:

    qconnect -j <job_number>

NOTE:: You must disconnect from the job by killing the 
qconnect session on the command line. Exiting out of the 
window will kill the job and thus the server.

### Getting GUI outputs from a tmux job ###
qconnect will silently attempt to use xpra to create a GUI with 
a tmux session. If xpra is installed, and you are running from an
X11 capable terminal, the GUI should instantly work. If any of those
things are not true, the GUI will silently fail to work.

To manually invoke the GUI component in a tmux session, run ``qconnect``
from within that session, it will attempt to connect to xpra and give you
information.  Follow the instructions and xpra will either connect or will
give you a useful error message.

To manually connect to a GUI component of a tmux job only, run:

    qconnect --connect-gui <job_number>

This will also work for a single gui job, where it will do exactly the 
same thing at the -j flag

### Option Summary ###
qconnect's basic functions require no arguments. However it is possible to
configure it fairly extensively using the following options:

    -h, --help            show this help message and exit
    -l, --list            List running interactive jobs
    -c, --create          Create a new job even if existing jobs are running
    -j, --job_id JOB_ID   Specify the job_id to attach to, if not provided, top
                          hit assumed
    --vnc                 Create or attach to an XFCE VNC. Not recommended, but
                          sometimes useful
    --connect-gui JOB_ID  Connect to an xpra GUI on a running tmux job. You must
                          provide a job number

NOTE: The -j and --connect-gui options will not be available if no jobs
are running or if you run qconnect from within an existing qconnect session

The following options can only be used for the creation of jobs:

    -g, --gui GUI         Create a GUI job with this program
                          (requires an executable as an argument)
    -n, --name NAME       A name for the job, not required
    -t, --cores CORES     Number of threads to request for job
    -m, --mem MEM         Amount of memory to request for job in

Note on memory usage
--------------------
Note, if you do not use cgroups with torque, you need to be 
careful about memory. Programs like rstudio can have unpredictable 
memory requirements and can stall all other jobs on that node 
if they are not contained.

It is possible to use Docker for this task, but I have not
done that here.

