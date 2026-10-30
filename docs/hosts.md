# Hosts

How ploma moves between Claude Code and Codex, and how co-authors on Codex set up a clone.

## Switching hosts

ploma runs on one host at a time. The repo is onboarded for the host you ran onboard under; the onboard receipt records it. To switch, run onboard on the new host. The old host's files stay in place. The doctor reports `host_mismatch` until you run onboard on the new host.

## Co-authors on Codex

Co-authors on Codex run `$ploma:onboard` once per machine, after cloning. It is an absorption run: it writes nothing the repo already has and creates the machine-local `.ploma/plugin` link (`.ploma/` is gitignored, so a clone lacks it).
