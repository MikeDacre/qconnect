#! /bin/sh
if [[ $# != 1 ]]; then
  echo "Incorrect options or no options provided, aborting"
  echo "Must be run from the same directory as qconnect.py and qconnect.1.gz"
  echo "Requires root privileges"
  echo "Options:  -i : Install"
  echo "          -u : Uninstall"
  exit 1
fi

while getopts :iuh OPTS; do
  case $OPTS in
    i)  install -m755 qconnect.py /usr/bin/
        ln -s /usr/bin/qconnect.py /usr/bin/qconnect
        install -m644 qconnect.1.gz /usr/share/man/man1/
        ;;
    u)  rm /usr/bin/qconnect.py
        rm /usr/bin/qconnect
        rm /usr/share/man/man1/qconnect.1.gz
        ;;
    h)  echo "Requires root privileges"
        echo "Must be run from the same directory as qconnect.py and qconnect.1.gz"
        echo "Options:  -i : Install"
        echo "          -u : Uninstall"
        ;;
    \?) echo "Incorrect options or no options provided, aborting"
        echo "Must be run from the same directory as qconnect.py and qconnect.1.gz"
        echo "Requires root privileges"
        echo "Options:  -i : Install"
        echo "          -u : Uninstall"
        ;;
  esac
done
