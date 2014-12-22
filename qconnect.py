#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:fenc=utf-8 tabstop=4 expandtab shiftwidth=4 softtabstop=4
#
# Copyright © Mike Dacre <mike.dacre@gmail.com>
#
# Distributed under terms of the MIT license
"""
#====================================================================================
#
#          FILE: qconnect (python 3)
#        AUTHOR: Michael D Dacre, mike.dacre@gmail.com
#  ORGANIZATION: Stanford University
#       LICENSE: MIT License, Property of Stanford, Use as you wish
#       VERSION: 0.1
#       CREATED: 2014-12-17 18:07
# Last modified: 2014-12-22 13:30
#
#   DESCRIPTION: Create and connect to interactive tmux or GUI application in
#                the Torque interactive queue
#
#         USAGE: If you run without arguments, qconnect will search for a
#                running job, if it cannot find one, it will initiate a tmux
#                job. If there is an existing job, running it will
#                connect to that job. If there are multiple jobs present and no
#                arguments are given, qconnect will connect to the first job it
#                finds. If you explicitly request a GUI or TMUX job, it will
#                connect to the first one of those it finds, if one does not
#                exist, it will create a new one.
#
#                To explicitly create a new job pass '-c'
#
#====================================================================================
"""
import subprocess

# Aliases
from subprocess import check_output as rn
from re import findall as find
from re import split as s
import sys, os

# Config paramaters
default_cores     = 4
default_max_cores = 8   # Used for calculating memory request, not a hard cap
default_max_mem   = 16  # In GB, used to calculate a default memory based on number of cores

# Get UID
uid = rn('echo $UID', shell=True).decode('utf8').rstrip()

def check_queue(uid):
    """ Check the queue for any uid string, return job list with running
        node information. """

    qstat = rn(['qstat', '-u', uid, '-n', '-1']).decode('utf8').split('\n')[5:-1]

    # If there are no job return nothing
    if not qstat:
        return

    jobs = {}
    for i in qstat:
        f = s(r' +', i.rstrip())
        # Parse job string
        if f[11] == '--':
            node = ''
        else:
            nodes = set(find(r'node[0-9][0-9]', f[11]))
            if len(nodes) > 1:
                continue
            node = str(list(nodes)[0])

        # Skip completed jobs
        if f[9] == 'C':
            continue

        # Get name
        job_id = find(r'[0-9]+', f[0])[0]
        # Sometime I completely hate python. Why do I have to do this crap:
        p1 = subprocess.Popen(['qstat', '-f', job_id], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['grep', 'Job_Name'], stdin=p1.stdout, stdout=subprocess.PIPE)
        names = p2.communicate()[0].decode('utf8').rstrip().split(' ')[-1].split(',')

        # If non-segmented name, skip
        if len(names) < 2:
            continue

        name = ','.join(names[0:-1])

        # Check that this is actually one of our jobs
        if names[-1] == 'int_tmux':
            type = 'tmux'
        elif names[-1] == 'int_gui':
            type = 'gui'
        else:
            continue

        jobs[job_id] = {'queue'    : f[2],
                        'job_name' : name,
                        'type'     : type,
                        'node'     : node}

    return(jobs)

def check_list_and_run(job_list, gui=''):
    """ Take a list of existing jobs, and attach if possible.
        If no jobs running, create one.
        Default is tumx, adding gui="Some program" enables gui jobs """
    pass

def create_job(cores=default_cores, mem='', gui='', name=''):
    """ Create a job in the queue, wait for it to run, and then attach
        Ctl-C after submission will not kill job, it will only kill attach
        queue """

    # If gui check that executable exists
    if gui:
        prog = gui.split(' ')[0]
        if not os.path.isfile(prog):
            prog = os.path.basename(prog)
            for path in os.environ["PATH"].split(os.path.pathsep):
                if os.path.exists(path + "/" + prog):
                    prog = path + "/" + prog
                    break

            if not os.path.isfile(prog):
                print(prog + " is not a file. Make sure you provide the full path to the executable")
                sys.exit(1)

    # Figure out memory request
    try:
        mem = str(int(cores*default_max_mem/default_max_cores)) + 'GB' if not mem else str(int(mem)) + 'GB'
    except ValueError:
        print("Incorrect formatting for memory request, please submit an integer multiple in GB")
        sys.exit(1)

    # Create job name
    if gui:
        job_name = name + ',int_gui' if name else 'int_gui'
    else:
        job_name = name + ',int_tmux' if name else 'int_tmux'

    # Prep the job
    template = "#!/bin/bash\n#PBS -S /bin/bash\n"
    template = ''.join([template, "#PBS -q interactive", '\n#PBS -N ', job_name,
                        '\nPBS -l nodes=1:ppn=' + str(cores),
                        '\nPBS -l mem=' + mem])

    if gui:
        template = template + ("\n\ndisplay=$(echo $PBS_JOBID | sed 's#\..*##g')\n"
                               "program=\"" + gui + "\"\n"
                               "xpra start --no-pulseaudio --start-child=\"${program}\" --exit-with-children --no-daemon :$display\n"
                               "xpra stop :$display")
    else:
        template = template + ("\n\nsession_id=$(echo $PBS_JOBID | sed 's#\..*##g')\n"
                               "CMD=\"tmux new-session -s $session_id -d\"\n"
                               "$CMD\n"
                               "PID=$(ps axo pid,cmd | grep \"$CMD\" | grep -v grep | awk '{print $1}')\n"
                               "echo $PID\n\n"
                               "while true\n"
                               "do\n"
                               "  if kill -0 $PID > /dev/null 2>&1; then\n"
                               "    sleep 5\n"
                               "  else\n"
                               "    exit 0\n"
                               "  fi\n"
                               "done\n")

    pbs_command = (['qsub'])

    # Submit the job
    pbs_submit = subprocess.Popen(pbs_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    pbs_submit.stdin.write(template.encode())
    pbs_submit.stdin.close()

    # Get job number
    job_no = (pbs_submit.stdout.read().decode().rstrip())
    print('\t'.join([job_no, job_name]))

    return(job_no)

def attach_job(job_id):
    """ Attach to a currently running job, default is tmux, for gui add
        type='gui' """

    # Get details
    job_list = check_queue()
    try:
        node = job_list[job_id]['node']
        type = job_list[job_id]['type']
    except KeyError:
        print("Sorry, that job number doesn't exist. Please try again")
        print_jobs(job_list)
        sys.exit(1)

    if type == 'tmux':
        if rn('echo $TMUX', shell=True).decode().rstrip():
            print("You are already running a tmux session, sessions should be nested with care")
            print("To force run, unset the $TMUX variable, but I suggest you just detatch your")
            print("current session and try the same command again")
            return()

        # Actually attach to the session!
        subprocess.call(['ssh', node, '-t', 'tmux', 'a', '-t', job_id])

def print_jobs(job_list):
    """ Pretty print a list of running interactive jobs from create_queue """
    gui_jobs  = {}
    tmux_jobs = {}
    name_len = 20

    for k, v in job_list.items():
        name_len = max([name_len, len(v['job_name'])])
        if v['type'] == 'gui':
            gui_jobs[k] = v
        else:
            tmux_jobs[k] = v

    # Print the thing
    name_len = name_len + 2
    print("Job_ID".ljust(8) + "Job_Name".ljust(name_len) + "Job_Type".ljust(10) + "Queue".ljust(8) + "Node".ljust(10))
    print("=".ljust(6, '=') + "  " + "=".ljust(name_len - 2, '=') + "  " + "=".ljust(8, '=') + "  " + "=".ljust(6, '=') + "  " + "=".ljust(8, '='))
    for k,v in gui_jobs.items():
        print(k.ljust(8) + v['job_name'].ljust(name_len) + "GUI".ljust(10) + v['queue'].ljust(8) + v['node'].ljust(10))
    for k,v in tmux_jobs.items():
        print(k.ljust(8) + v['job_name'].ljust(name_len) + "TMUX".ljust(10) + v['queue'].ljust(8) + v['node'].ljust(10))

def _get_args():
    """Command Line Argument Parsing"""
    import argparse, sys

    parser = argparse.ArgumentParser(
                 description=__doc__,
                 formatter_class=argparse.RawDescriptionHelpFormatter)

    # Connection Arguments
    parser.add_argument('-l', '--list',   action='store_true', help="List running interactive jobs")
    parser.add_argument('-c', '--create', action='store_true', help="Create a new job even if existing jobs are running")
    parser.add_argument('-g', '--gui',    help="Create a GUI job with this program")
    parser.add_argument('-j', '--job_id',  default='', help="Specify the job_id to attach to, if not provided, top hit assumed")

    # Job control arguments - Only relevant for creation
    parser.add_argument('-n', '--name',  help="A name for the job, not required")
    parser.add_argument('-t', '--cores', type=int, default=default_cores, help="Number of threads to request for job")
    parser.add_argument('-m', '--mem',   type=int, help="Amount of memory to request for job in GB (integer)")

    return parser

# Main function for direct running
def main():
    """Run directly"""
    from os  import getuid
    from pwd import getpwuid

    # Get commandline arguments
    parser = _get_args()
    args = parser.parse_args()

    name = args.name if args.name else ''

    # Don't bother checking queue if the user just wants a new job
    if args.create:
        job_id = create_job(cores=args.cores, mem=args.mem, gui=args.gui, name=name)
        #attach_job(job_id)
        return

    # Get job list from queue
    job_list = check_queue(getpwuid(getuid()).pw_name)

    # Print the list if that is all that is required
    if args.list:
        if job_list:
            print_jobs(job_list)
        else:
            print("No running jobs")
        return

    # If a job ID is specified, just jump straight to attachment
    if args.job_id:
        attach_job(job_id)

    # Start the job creation and connection system
    if args.gui:
        check_list_and_run(job_list, gui=True)
        return
    else:
        check_list_and_run(job_list, gui=False)
        return

# The end
if __name__ == '__main__':
    main()
