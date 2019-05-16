# PyShell

A simple UNIX shell written in Python 3.

**Notice that this shell is not meant for production usage.**

## Features

- Redirection, piping, and their common combinations.

- Common `^C` (ignoring current input and start again), `^D` (exit or logout) shortcuts are supported.

- Arrow keys are supported. You can press them to see the input history.

## Known Defects

- "Background job" feature is incomplete.

- ~~When using redirection and an error occurs, the error message may be also redirected into the file.~~

- Auto complete is not supported.
