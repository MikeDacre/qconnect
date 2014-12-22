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
# Last modified: 2014-12-18 18:33
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
import sys

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

def check_list_and_run(job_list, gui=false):
    """ Take a list of existing jobs, and attach if possible.
        If no jobs running, create one.
        Default is tumx, adding gui=true enables gui jobs """
    pass

def create_job(gui=false):
    """ Create a job in the queue, wait for it to run, and then attach
        Ctl-C after submission will not kill job, it will only kill attach
        queue """
    pass

def attach_job(job_id, gui=false):
    """ Attach to a currently running job, default is tmux, for gui add
        gui=true """
    pass

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

    # Optional Arguments
    parser.add_argument('-l', '--list',   action='store_true', help="List running interactive jobs")
    parser.add_argument('-c', '--create', action='store_true', help="Create a new job even if existing jobs are running")
    parser.add_argument('-g', '--gui',    action='store_true', help="Create a GUI job, without this flag, tmux is assumed")
    parser.add_argument('-j', '--jobid',  default='', help="Specify the jobid to attach to, if not provided, top hit assumed")

    return parser

# Main function for direct running
def main():
    """Run directly"""
    from os  import getuid
    from pwd import getpwuid

    # Get commandline arguments
    parser = _get_args()
    args = parser.parse_args()

    # Don't bother checking queue if the user just wants a new job
    if args.create:
        if args.gui:
            create_job(gui=true)
        else:
            create_job(gui=false)

    # Get job list from queue
    job_list = check_queue(getpwuid(getuid()).pw_name)

    # Print the list if that is all that is required
    if args.list:
        if job_list:
            print_jobs(job_list)
        else:
            print("No running jobs")
        sys.exit(0)

    # If a job ID is specified, just jump straight to attachment
    if args.jobid:
        attach_job(jobid, job_list)

    # Start the job creation and connection system
    if args.gui:
        check_list_and_run(job_list, gui=true)
    else:
        check_list_and_run(job_list, gui=false)

# The end
if __name__ == '__main__':
    main()
