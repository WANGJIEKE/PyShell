# PyShell

A simple UNIX shell written in Python 3.

**Notice that this shell is not meant for production usage.**

## Features

- "Background" process.

- Redirection, piping, and their common combinations.

- Common `^C` (ignoring current input and start again), `^D` (exit or logout) shortcuts are supported.

- Arrow keys are support. You can press them to see the input history.

## Known Defects

- The background process is not the TRUE background process. The "background" process will "fight" with the shell on the inputs in `sys.stdin`.

- When using redirection and an error occurs, the error message may be also redirected into the file.

- Auto complete is not supported.
