qconnect
========
Uses torque, tmux, xpra and optionally vncserver to create persistent
interactive sessions on compute nodes.

In its simplest form, it will create a tmux session on a compute node
with an xpra GUI running in the background. When the user detaches tmux
xpra also detaches. Running qconnect again will reattach to the previous
tmux and xpra sessions.

The program can also create standalone GUI applications on a compute node,
and create and attach to a vnc server on a compute node if desired.

Further usage information is below and in the man page. Running ``qconnect -h``
also provides valuable information.

Installation
------------
You can find the latest package [here](https://github.com/MikeDacre/qconnect/blob/master/packages/qconnect_latest.tar.gz)
and the GPG signature [here](https://github.com/MikeDacre/qconnect/blob/master/packages/qconnect_latest.tar.gz)

Prerequisites:

- torque
- tmux
- xpra (optional)
- X11 (optional)
- tigervnc (optional)

To install, simply unpack the archive, and put qconnect.py somewhere
in your ``$PATH``. You can also put qconnect.1.gz into your man path if you
wish. Running the ``install.sh`` program as root will do this for you, running
as ``install.sh -u`` will uninstall.

If you are on arch linux, I have an installation package
available on the [aur](https://aur.archlinux.org/packages/qconnect/)

You will need a batch queue available to use this program, and every compute
node will need to have tmux installed. You can set your queue name at the top
of the qconnect.py file. The default queue name is 'interactive'. You will also
need to set your compute node max CPU and memory levels, the defaults are 8
cores and 32GB of memory. Be aware that the torque queue must be a batch queue.
My suggestion is to create a queue called 'interactive' that can take both
batch and interactive jobs, disallow interactive jobs on every other queue, and
set the max user run limit ion the 'interactive' queue to 3 jobs.

_NOTE: Right now qconnect is only compatible with linux._

### Important Installation Notes ###
qconnect can *seriously* mess up your batch system if torque is not configured
correctly. Most importantly, it is necessary to have an execution queue named
'interactive' (you can change this queue name in the source code), and to
make sure this queue is well configured. I _strongly_ suggest limiting
users to a maximum of 3 interactive jobs.

Additionally, unless you configure hwloc and cgroups in your torque config,
it isn't possible to enforce the CPU and memory request, so it is possible
for a user to overrun the entire system, and there is nothing torque can do
about that.

Finally, and probably most importantly, if torque is set to treat one node as one
machine, every user will get a whole machine with each job they run. That will
waste resources very badly. qconnect does not allow more than one node, and
uses ``ppn`` to request additional cores on a node. If you use a _1 node = 1 machine_
setup, this will hugely waste resources and you should edit this source code
before using it.

Usage
-----

### Starting a job ###
Starting an interactive tmux job with a backend GUI is very simple,
just run ``qconnect`` from the command line. If you are running
from a console with X11 support, everything will just work. If qconnect
detects an existing job, it will connect to that session, if it does
not, it will create a new one.

Be aware that the server-side jobs will run for up to 5 seconds after they are
terminated, if you run qconnect within that time without arguments, it will
attempt to reconnect to the dying job, and you will get an error.

Note, it is possible to modify the number of cores and amount of
memory using the options described below.

If you plan on running multiple simultaneous tmux sessions, it is wise
to name them using the ``-N`` flag. There is not a need to
use multiple sessions though, and it probably isn't a good idea.
The ``qconnect`` program requests 1 node by default, most torque
configurations treat this as one core, which means if you run 4
tmux sessions at the same time and you have quad core compute nodes,
you will be taking up the whole machine. *Not wise*.

NOTE: You will see errors such as these from some X11 programs:

    XIO:  fatal IO error 11 (Resource temporarily unavailable) on X server ":442611"
          after 221 requests (221 known processed) with 0 events remaining.

These are harmless warnings and can be ignored

#### GUI Only Jobs ####
The can be started by providing the ``-g`` flag, followed by a command
argument. e.g.:

    qconnect -g rstudio-bin

This works for most applications, but some, most notably matlab, fail
because they can tell they are being run from a batch system. In those
cases, get a GUI working in the tmux session using the instructions here,
and run the application from there.

#### VNC ####
It is possible to get a VNC connection to a node using the ``--vnc`` flag.
I don't suggest this, as it wastes resources, but it is possible.

Detailed setup instructions are available on the man page.

### Connecting to a job ###
To connect to the job, you can just run ``qconnect``. If you have
multiple jobs just find the job number you want with ``qconnect -l``
and run:

    qconnect <job_number>

NOTE:: You must disconnect from the job by either detaching or
killing the qconnect session from the command line. Exiting out
of any window will kill the application itself.

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
    --vnc                 Create or attach to an XFCE VNC. Not recommended, but
                          sometimes useful
    --connect-gui JOB_ID  Connect to an xpra GUI on a running tmux job. You must
                          provide a job number

The following options can only be used for the creation of jobs:

    -g, --gui GUI         Create a GUI job with this program
                          (requires an executable as an argument)
    -n, --name NAME       A name for the job, not required
    -t, --cores CORES     Number of threads to request for job
    -m, --mem MEM         Amount of memory to request for job in

NOTE: The --gui and --connect-gui option will not be available if xpra is not
installed. Additionally, --connect-gui will not appear if there are not jobs in
the queue.

Note on memory usage
--------------------
Note, if you do not use cgroups with torque, you need to be
careful about memory. Programs like rstudio can have unpredictable
memory requirements and can stall all other jobs on that node
if they are not contained.

It is possible to use Docker for this task, but I have not
done that here.

