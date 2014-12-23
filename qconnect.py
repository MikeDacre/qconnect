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
# Last modified: 2014-12-22 18:29
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
from os  import getuid
from pwd import getpwuid
from time import sleep
import sys, os

# Config paramaters
default_cores     = 4
default_max_cores = 8   # Used for calculating memory request, not a hard cap
default_max_mem   = 16  # In GB, used to calculate a default memory based on number of cores

# Get UID
uidno = rn('echo $UID', shell=True).decode('utf8').rstrip()
uid   = getpwuid(getuid()).pw_name

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

        name = ','.join(names[0:-1])

        # Check that this is actually one of our jobs
        if names[-1] == 'int_tmux':
            type = 'tmux'
        elif names[-1] == 'int_gui':
            type = 'gui'
        else:
            continue

        # Fix queue name
        queue = 'interactive' if 'interact' else queue
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

def try_to_attach(job_id):
    """ Try to attach to job_id every two seconds until success or error """
    while 1:
        s = check_job(job_id)
        if s:
            if s == 'Q':
                continue
            elif s == 'C':
                print("Job error, job already completed. Either you completed it normally")
                print("Or it errored out and failed. Check `qstat -f" + job_id + "for more")
                print("details. Exiting")
                sys.exit(3)
            elif s == 'R':
                attach_job(job_id)
                break
            else:
                print("Job attach failed due to a failed state in the queue. This may mean an old job")
                print("is in the process of exiting")
                sys.exit(10)
        else:
            print("Queue appears empty, perhaps try running again, or check qstat. It may")
            print("be necessary to adjust the sleep length")
        sleep(2)

def check_list_and_run(job_list, cores=default_cores, mem='', gui='', name=''):
    """ Take a list of existing jobs, and attach if possible.
        If no jobs running, create one.
        Default is tumx, adding gui="Some program" enables gui jobs """
    for k,v in job_list.items():
        if v['type'] == 'tmux':
            attach_job(k)
            return
    job_id = create_job(cores=cores, mem=mem, gui=gui, name=name)
    print("Job created, waiting to attach. If the queue is long, you can safely Ctrl-C")
    print("and come back when the job is running. Then just run qconnect -j " + job_id)
    print("to attach\n")
    sleep(2)
    try_to_attach(job_id)
    return

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
    job_no = find(r'[0-9]+', job_no)[0]
    print("Job", job_name, "created with job id", job_no, "\n")

    return(job_no)

def attach_job(job_id):
    """ Attach to a currently running job, default is tmux, for gui add
        type='gui' """

    # Get details
    job_list = check_queue(uid)
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
        print(name)
        print(k.ljust(8) + name.ljust(name_len) + "GUI".ljust(10) + v['queue'].ljust(13) + v['node'].ljust(8) + v['state'].ljust(10))
    for k,v in tmux_jobs.items():
        name = v['job_name'] if v['job_name'] else v['type']
        print(k.ljust(8) + name.ljust(name_len) + "TMUX".ljust(10) + v['queue'].ljust(13) + v['node'].ljust(8) + v['state'].ljust(10))

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

    # Get commandline arguments
    parser = _get_args()
    args = parser.parse_args()

    name = args.name if args.name else ''

    # Don't bother checking queue if the user just wants a new job
    if args.create:
        job_id = create_job(cores=args.cores, mem=args.mem, gui=args.gui, name=name)
        print("Job created, waiting to attach. If the queue is long, you can safely Ctrl-C")
        print("and come back when the job is running. Then just run qconnect -j" + job_id)
        print("to attach")
        attach_job(job_id)
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
    if args.job_id:
        attach_job(args.job_id)

    # Start the job creation and connection system
    check_list_and_run(job_list, cores=args.cores, mem=args.mem, gui=args.gui, name=args.name)

# The end
if __name__ == '__main__':
    main()
