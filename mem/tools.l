# mem/tools.l spec=1
# Canonical commands. Agents run these strings; do not invent equivalents.
# name|command
snap|python3 mem/mem.py snap
check|python3 mem/mem.py check
new|python3 mem/mem.py new
add|python3 mem/mem.py add <handle> <KIND or ID> <status> "<text>"
review|python3 mem/mem.py review <via> <id> ok|redo [note]
test|python3 -m unittest mem/test_mem.py
