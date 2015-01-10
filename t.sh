#PBS -S /bin/bash
#PBS -q interactive
#PBS -N int_tmux
#PBS -l nodes=1:ppn=1
#PBS -l mem=4GB
#PBS -e /home/dacre/.int_tmux.error
#PBS -o /dev/null

export QCONNECT=tmux

session_id=$(echo $PBS_JOBID | sed 's#\..*##g')
if xpra start --no-pulseaudio :$session_id >/dev/null 2>/dev/null; then
    export DISPLAY=:$session_id
fi
echo $DISPLAY
CMD="tmux new-session -s $session_id -d"
$CMD
PID=$(ps axo pid,user,cmd | grep tmux | grep $USER | grep -v grep | awk '{print $1}')
while true
do
  if kill -0 $PID > /dev/null 2>&1; then
    if [[ ! $(tmux ls | grep $session_id) ]]; then
      xpra stop :$session_id >/dev/null 2>/dev/null
      exit 0
    else
      sleep 5
    fi
  else
    exit 0
  fi
done

