qguiconnect
===========
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

    qguiconnect <job_number>

NOTE:: You must disconnect from the job by killing the 
qguiconnect session on the command line. Exiting out of the 
window will kill the job and thus the server.

Note on memory usage
--------------------
Note, if you do not use cgroups with torque, you need to be 
careful about memory. Programs like rstudio can have unpredictable 
memory requirements and can stall all other jobs on that node 
if they are not contained.

It is possible to use Docker for this task, but I have not
done that here.

