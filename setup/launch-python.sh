#!/bin/bash

tmux new -d -s sparkfun
tmux send-keys -t sparkfun 'cd ~pi/sparkfun-avc/setup' c-m
tmux send-keys -t sparkfun 'export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3' c-m
tmux send-keys -t sparkfun 'source /usr/local/bin/virtualenvwrapper.sh' c-m
tmux send-keys -t sparkfun 'workon sparkfun' c-m
tmux send-keys -t sparkfun './rooter -m main -l /tmp/out.log' c-m