#!/bin/sh

reset
tail -n 200 ~/ONIDbot/log.txt
echo ""
~/PyCluster/PyCluster.py status
echo ""
echo "Last backup: $(date -d @$(ls -S ~/ONIDbot/backups/ | head -n 1 | sed 's/\.json$//'))"
echo ""