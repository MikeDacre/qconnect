#!/usr/bin/env python3
# vim:fenc=utf-8 tabstop=4 expandtab shiftwidth=4 softtabstop=4
"""
#====================================================================================#
#                                                                                    #
#          FILE: qconnect (python 3)                                                 #
#        AUTHOR: Michael D Dacre, mike.dacre@gmail.com                               #
#       LICENSE: MIT License, Property of Stanford, Use as you wish                  #
#       VERSION: 1.8.0-beta                                                          #
# Last modified: 2015-01-09 12:01
#                                                                                    #
#   DESCRIPTION: Create and connect to interactive tmux or GUI application in        #
#                the Torque interactive queue                                        #
#                                                                                    #
#         USAGE: If you run without arguments, qconnect will search for a            #
#                running job, if it cannot find one, it will initiate a tmux         #
#                job. If there is an existing job, running it will                   #
#                connect to that job.                                                #
#                                                                                    #
#                Note: If you want to use VNC, extra configuration is required,      #
#                                                                                    #
#                For more info see the man page                                      #
#                                                                                    #
#====================================================================================#
"""
##############################################
#                                            #
#         Global Config Options              #
#           Set To Your Needs                #
#                                            #
##############################################

# Queue Options
interactive_queue = 'interactive'
short_queue_name  = 'interact'   # The queue name displayed when you run qstat -n -1

# Interactive Node Options
default_cores     = 1
default_max_cores = 8   # Used for calculating memory request, set to total cores on node
default_max_mem   = 32  # In GB, used to calculate a default memory based on number of cores

# Debuging - prints a bunch of stuff
debug = False

##############################################
#                                            #
#      Do Not Edit Below This Line           #
#                                            #
##############################################

## Imports
import subprocess
import sys, os

# Aliases
from subprocess import check_output as rn
from re         import findall      as find
from re         import split        as s
from sys        import stderr
from os         import getuid
from pwd        import getpwuid
from time       import sleep

## Global Variables

# Get UID
uidno = rn('echo $UID', shell=True).decode('utf8').rstrip()
uid   = getpwuid(getuid()).pw_name

# Version string
version = '1.8.0-beta'

## Functions

def check_queue(uid):
    """ Check the queue for any uid string, return job list with running
        node information. """
    from re import compile as mkregex

    qstat = rn(['qstat', '-u', uid, '-n', '-1']).decode('utf8').rstrip().split('\n')[5:]

    # If there are no job return nothing
    if not qstat:
        return

    jobs = {}
    for i in qstat:
        f = s(r' +', i.rstrip())

        # Only look at jobs in the interactive queue
        if not f[2] == short_queue_name:
            continue

        # Skip completed jobs
        if f[9] == 'C':
            continue

        # Get node name, if there is one
        if f[11] == '--':
            node = ''
        else:
            nodes = set(find(r'node[0-9][0-9]', f[11]))
            if len(nodes) > 1:
                continue
            node = str(list(nodes)[0])

        # Get job number
        job_id = find(r'[0-9]+', f[0])[0]

        # Now that we have a limited job set, use qstat -f to get the
        # complete job and queue name
        find_queue = mkregex(r'queue = (.*)$')
        find_name  = mkregex(r'Job_Name = (.*)$')

        for i in subprocess.check_output(['qstat', '-f', '442597']).decode().rstrip().split('\n'):
            # Get Queue Name
            if find_queue.search(i):
                try:
                    queue = find_queue.findall(i)[0]
                except IndexError:
                    # Queue parsing failed, report this and continue
                    print("Failed to parse queue for job number:{:^3}\nskipping".format(job_id), file=stderr)
                    continue
                if not queue == interactive_queue:
                    continue
            elif find_name.search(i):
                try:
                    names = find_name.findall(i)[0].split('_')
                except IndexError:
                    # Queue parsing failed, report this and continue
                    print("Failed to parse queue for job number:{:^3}\nskipping".format(job_id), file=stderr)
                    continue

        name       = '_'.join(names[:-2])
        identifier = '_'.join(names[-2:])

        # Check that this is actually one of our jobs
        if identifier == 'int_tmux':
            type = 'tmux'
        elif identifier == 'vnc':
            type = 'vnc'
        elif identifier == 'gui':
            type = 'gui'
        else:
            continue

        # Fix queue name
        jobs[job_id] = {'queue'    : queue,
                        'job_name' : name,
                        'type'     : type,
                        'node'     : node,
                        'state'    : f[9]}

    return(jobs)

def check_job(job_id):
    """ Check a job_id, if it is running return state, else return False """
    qstat = rn(['qstat', job_id]).decode('utf8').split('\n')[2:3]

    if not qstat:
        return(False)

    return(s(r' +', qstat[0].rstrip())[4])

def try_to_attach(job_id, attempt_gui=False):
    """ Try to attach to job_id every two seconds until success or error """
    try:
        print("Waiting to attach. If the queue is long, you can safely Ctrl-C")
        print("and come back when the job is running. Then just run qconnect -j " + job_id)
        print("to attach\n")

        count = 1
        while 1:
            count = count - 1
            sleep(1)
            s = check_job(job_id)
            if s:
                if s == 'Q':
                    if count == 0:
                        print("Job is still queueing, we will attach ASAP")
                        count = 20
                    continue
                elif s == 'C':
                    print("Job error, job already completed. Either you completed it normally")
                    print("Or it errored out and failed. Check `qstat -f " + job_id + "` for more")
                    print("details. Exiting")
                    sys.exit(3)
                elif s == 'R':
                    sleep(1)
                    s = check_job(job_id)
                    if s == 'R':
                        attach_job(job_id, attempt_gui)
                    else:
                        print("Job died before it even started. Sorry")
                        sys.exit(3)
                    return
                else:
                    print("Job attach failed due to a failed state in the queue. This may mean an old job")
                    print("is in the process of exiting")
                    sys.exit(10)
            else:
                print("Queue appears empty, perhaps try running again, or check qstat. It may")
                print("be necessary to adjust the sleep length")

    except KeyboardInterrupt:
        print("Goodbye! To reconnect run qconnect -j [or --connect-gui] " + job_id)

def check_list_and_run(job_list, cores=default_cores, mem='', gui='', name='', vnc=False):
    """ Take a list of existing jobs, and attach if possible.
        If no jobs running, create one.
        Default is tumx, adding gui="Some program" enables gui jobs """
    if gui:
        job_type = 'gui'
    elif vnc:
        job_type = 'vnc'
    else:
        job_type = 'tmux'

    # Attach first job that matches request
    queued_job = ''
    if job_list:
        for k,v in job_list.items():
            if v['type'] == job_type:
                if v['state'] == 'Q':
                    queued_job = k
                elif v['state'] == 'R':
                    try_to_attach(k)
                    return
        if queued_job:
            try_to_attach(queued_job)

    # If that fails, there are no running jobs, so make one
    job_id = create_job(cores=cores, mem=mem, gui=gui, name=name, vnc=vnc)
    sleep(2)
    try_to_attach(job_id)
    return

def create_job(cores=default_cores, mem='', gui='', name='', vnc=False):
    """ Create a job in the queue, wait for it to run, and then attach
        Ctl-C after submission will not kill job, it will only kill attach
        queue """

    # Figure out memory request
    try:
        mem = str(int(cores*default_max_mem/default_max_cores)) + 'GB' if not mem else str(int(mem)) + 'GB'
    except ValueError:
        print("Incorrect formatting for memory request, please submit an integer multiple in GB")
        sys.exit(1)

    # Create job name
    if gui:
        gui_name = gui.split(' ')[0]
        job_name = name + '_' + gui_name + '_int_gui' if name else gui_name + '_int_gui'
    elif vnc:
        job_name = name + '_int_vnc' if name else 'int_vnc'
    else:
        job_name = name + '_int_tmux' if name else 'int_tmux'

    # Prep the job
    template = "#!/bin/bash\n#PBS -S /bin/bash\n"
    template = ''.join([template, "#PBS -q interactive", '\n#PBS -N ', job_name,
                        '\n#PBS -l nodes=1:ppn=' + str(cores),
                        '\n#PBS -l mem=' + mem,
                        '\n#PBS -e ' + os.environ['HOME'] + '/.' + job_name + '.error',
                        '\n#PBS -o /dev/null'])

    if gui:
        template = template + ("\n\nexport QCONNECT=gui"
                               "\n\njob_id=$(echo $PBS_JOBID | sed 's#\..*##g')\n"
                               "xpra start --no-pulseaudio :$job_id\n"
                               "export DISPLAY=:${job_id}\n"
                               "sleep 1\n" +
                               gui + "\n"
                               "PID=$!\n"
                               "sleep 1\n"
                               "while true\n"
                               "do\n"
                               "  if kill -0 $PID > /dev/null 2>&1; then\n"
                               "    sleep 5\n"
                               "  else\n"
                               "    xpra stop :${job_id}\n"
                               "    exit 0\n"
                               "  fi\n"
                               "done\n")

    elif vnc:
        template = template + ("\n\nexport QCONNECT=vnc\n\nvncserver -geometry 1280x1024 -fg\n")

    else:
        template = template + ( "\n\nexport QCONNECT=tmux"
                                "\n\nsession_id=$(echo $PBS_JOBID | sed 's#\..*##g')\n"
                                "if xpra start --no-pulseaudio :$session_id >/dev/null 2>/dev/null; then\n"
                                "    export DISPLAY=:$session_id\n"
                                "fi\n"
                                "CMD=\"tmux new-session -s $session_id -d\"\n"
                                "$CMD\n"
                                "PID=$(ps axo pid,user,cmd | grep tmux | grep $USER | grep -v grep | awk '{print $1}')\n"
                                "while true\n"
                                "do\n"
                                "  if kill -0 $PID > /dev/null 2>&1; then\n"
                                "    if [[ ! $(tmux ls | grep $session_id) ]]; then\n"
                                "      xpra stop :$session_id >/dev/null 2>/dev/null\n"
                                "      exit 0\n"
                                "    else\n"
                                "      sleep 5\n"
                                "    fi\n"
                                "  else\n"
                                "    exit 0\n"
                                "  fi\n"
                                "done\n")
    if debug:
        print(template)

    pbs_command = (['qsub'])

    # Submit the job
    pbs_submit = subprocess.Popen(pbs_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    pbs_submit.stdin.write(template.encode())
    pbs_submit.stdin.close()

    # Get job number
    job_no = (pbs_submit.stdout.read().decode().rstrip())
    job_no = find(r'[0-9]+', job_no)[0]
    print("Job", job_name, "created with job id", job_no, "\n")
    sleep(1)

    return(job_no)

def attach_job(job_id, attempt_gui=False):
    """ Attach to a currently running job, default is tmux.
        To attach to a GUI running in tmux, pass attempt_gui """

    # Get details
    job_list = check_queue(uid)
    try:
        node  = job_list[job_id]['node']
        type  = job_list[job_id]['type']
        state = job_list[job_id]['state']
    except KeyError:
        print("Sorry, that job number doesn't exist. Please try again")
        print_jobs(job_list)
        sys.exit(1)

    if not state == 'R':
        print("Job not running, cannot attach")
        return

    if type == 'gui' or attempt_gui:
        print("You MUST NOT close your program by closing the window unless you want to")
        print("terminate your session\n")
        print("To preserve your session, you need to Ctrl-C in the command line, not close")
        print("the window\n")
        sleep(2)
        subprocess.call(['xpra', 'attach', 'ssh:' + uid + '@' + node + ':' + job_id])
        return

    elif type == 'tmux':
        if rn('echo $TMUX', shell=True).decode().rstrip():
            print("You are already running a tmux session, sessions should be nested with care")
            print("To force run, unset the $TMUX variable, but I suggest you just detatch your")
            print("current session and try the same command again")
            return

        # Attempt to initially attach to xpra, fail gracefully without
        # notifying user
        GUI_PID=''
        if subprocess.call("xpra attach ssh:dacre@node01:442597 >/dev/null 2>/dev/null &", shell=True) == 0:
            GUI_PID = subprocess.check_output('ps axo pid,user,cmd | grep "xpra attach" | grep "442597$"| awk \'{print $1}\'', shell=True).decode().rstrip()

        # Actually attach to the session!
        job_string = ' '.join(['ssh', node, '-t', 'tmux', 'a', '-t', job_id])
        subprocess.call(job_string, shell=True)

        # Kill GUI if open
        if GUI_PID:
            subprocess.call(['kill', GUI_PID])

    elif type == 'vnc':
        # Get VNC Port
        ports = []
        files = subprocess.check_output('ssh ' + node + ' "ls $HOME/.vnc"', shell=True).decode().rstrip().split('\n')
        for i in files:
            if i.startswith(node) and i.endswith('pid'):
                    port = find(r':([0-9]+)\.pid', i)[0]
                    ports.append(port)

        if not ports:
            print("It appears no VNC servers are running on the selected server.")
            print("If the job is still running in the queue, there is a problem.")
            print("Try clearing out the *.log and *.pid files in $HOME/.vnc, and killing")
            print("the running VNC queue job")
            return

        if len(ports) > 1:
            print("There is more than one vnc server running for you on that node.")
            print("That isn't allowed and I don't know which one to join. It may")
            print("be that your last session exited without cleaning $HOME/.vnc")
            print("Check in there and clean out log files for vnc servers that")
            print("aren't running to prevent problems")
            return

        subprocess.call(['vncviewer', node + ':' + ports[0]])
        return

    else:
        print("I don't understand the job type")
        return

def print_jobs(job_list):
    """ Pretty print a list of running interactive jobs from create_queue """
    gui_jobs  = {}
    tmux_jobs = {}
    name_len = 10

    for k, v in job_list.items():
        name_len = max([name_len, len(v['job_name'])])
        if v['type'] == 'gui':
            gui_jobs[k] = v
        else:
            tmux_jobs[k] = v
    name_len = name_len + 2

    # Print the thing
    print("Job_ID".ljust(8) + "Job_Name".ljust(name_len) + "Job_Type".ljust(10) + "Queue".ljust(13) + "Node".ljust(8) + "State".ljust(7))
    print("=".ljust(6, '=') + "  " + "=".ljust(name_len - 2, '=') + "  " + "=".ljust(8, '=') + "  " + "=".ljust(11, '=') + "  " + "=".ljust(6, '=') + "  " + "=".ljust(5, '='))
    for k,v in gui_jobs.items():
        name = v['job_name'] if v['job_name'] else v['type']
        print(k.ljust(8) + name.ljust(name_len) + "GUI".ljust(10) + v['queue'].ljust(13) + v['node'].ljust(8) + v['state'].ljust(10))
    for k,v in tmux_jobs.items():
        name = v['job_name'] if v['job_name'] else v['type']
        print(k.ljust(8) + name.ljust(name_len) + "TMUX".ljust(10) + v['queue'].ljust(13) + v['node'].ljust(8) + v['state'].ljust(10))

def create_gui(display_id):
    """ Use xpra to create a gui. Simply set the display variable if it isn't already
        set and xpra is already running.
        Returns 'new' or 'old' on success and False on failure"""

    # Check for a GUI
    session_id = rn("xpra list| grep LIVE 2>/dev/null| grep ':" + display_id + "$' 2>/dev/null| sed 's/.*://g'", shell=True).decode()

    # If doesn't exit, create a session
    if session_id:
        type = 'old'
    else:
        type = 'new'
        try:
            subprocess.check_call(['xpra', 'start', '--no-pulseaudio', ':' + display_id])
        except subprocess.CalledProcessError as err:
            print("xpra failed with the following error:\n{0}".format(err))
            return(False)

    # Set DISPLAY and return success
    os.environ['DISPLAY'] = ':' + session_id
    return(type)

def check_state():
    """ Check if we are already in a qconnect session and return type """
    try:
        return(os.environ['QCONNECT'])
    except KeyError:
        return(False)

def set_display(type):
    """ Check if running in qconnect, and then set xpra display """
    if type == 'tmux':
        job_id = os.environ['PBS_JOBID'].split('.')[0]
        type = create_gui(job_id)
        if type == 'old':
            print("GUI already running on this node.")
        elif type == 'new':
            print("\nStarted a new GUI for you.")
        else:
            print("Attempt to create GUI failed. Sorry")
            return
        print("Run this command in your shell:\n\n"
              "export DISPLAY=:" + job_id + '\n')
        print("To connect to the gui, from the login node, run:\n\n",
              "{:^50}\n{:^50}\n{:^50}".format("qconnect --connect-gui " + job_id,
              "or",
              "xpra attach ssh:" + os.environ['USER'] + '@' + rn('hostname').decode().rstrip() + ':' + job_id))
    else:
        print("Not running in a qconnect session, not creating GUI")

def _get_args():
    """Command Line Argument Parsing"""
    import argparse, sys

    type = check_state()
    queue = True if check_queue(uid) else False
    if type:
        description = ("NOTE: You are currently in a qconnect " + type + " session\n\n"
                       "You will be unable to attach to other tmux qconnect jobs\n"
                       "Also, if you are not connected to the xpra DISPLAY, vnc and\n"
                       "GUI jobs will not run, they will initiate, but you won't see them\n\n"
                       "To create and initialize a display, run qconnect with no options\n")
    else:
        description = __doc__

    parser = argparse.ArgumentParser(
                 description=description,
                 formatter_class=argparse.RawDescriptionHelpFormatter)

    # Connection Arguments
    parser.add_argument('-l', '--list',   action='store_true', help="List running interactive jobs")
    parser.add_argument('-c', '--create', action='store_true', help="Create a new job even if existing jobs are running")
    if not type and queue:
        parser.add_argument('-j', '--job_id',  default='', help="Specify the job_id to attach to, if not provided, top hit assumed")

    # Job control arguments - Only relevant for creation
    parser.add_argument('-g', '--gui',   help="[Create Only] Create a GUI job with this program (requires an executable as an argument)")
    parser.add_argument('-n', '--name',  help="[Create Only] A name for the job, not required")
    parser.add_argument('-t', '--cores', type=int, default=default_cores, help="[Create Only] Number of threads to request for job")
    parser.add_argument('-m', '--mem',   type=int, help="[Create Only] Amount of memory to request for job in GB (integer)")

    # VNC
    parser.add_argument('--vnc', action='store_true', help="Create or attach to an XFCE VNC. Not recommended, but sometimes useful")

    # GUI Connect if job running
    if not type and queue:
        parser.add_argument('--connect-gui', dest='connect', help=("Connect to an xpra GUI on a running tmux job. You must provide a job number"))

    # Version
    parser.add_argument('-v', '--version', action='store_true', help="Display version number")

    return parser

# Main function for direct running
def main():
    """Run directly"""

    # Get commandline arguments
    parser = _get_args()
    args = parser.parse_args()

    # Print version number
    if args.version:
        print(version)
        return

    name = args.name if args.name else ''

    # Don't bother checking queue if the user just wants a new job
    if args.create and not args.vnc:
        job_id = create_job(cores=args.cores, mem=args.mem, gui=args.gui, name=name)
        sleep(2)
        try_to_attach(job_id)
        return

    # Get job list from queue
    job_list = check_queue(uid)

    # Print the list if that is all that is required
    if args.list:
        if job_list:
            print_jobs(job_list)
        else:
            print("No running jobs")
        return

    # If a job ID is specified, just jump straight to attachment
    try:
        if args.job_id:
            try_to_attach(args.job_id)
            return
    except AttributeError:
        pass

    # Check if we are already in a session
    type = check_state()
    try:
        if type == 'tmux':
            set_display(type)
            return
        elif args.connect:
            try_to_attach(args.connect, attempt_gui=True)
            return
    except AttributeError:
        pass

    # Start the job creation and connection system
    check_list_and_run(job_list, cores=args.cores, mem=args.mem, gui=args.gui, name=args.name, vnc=args.vnc)

# The end
if __name__ == '__main__':
    main()
