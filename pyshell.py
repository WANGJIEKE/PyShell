# -*- coding: utf-8 -*-
# Created with PyCharm
# @Time    : 2019-05-14 19:36
# @Author  : Tongjie Wang

import cmd
import getpass
import itertools
import os
import shlex
import signal
import socket
import sys


class PyShell(cmd.Cmd):
    def __init__(self):
        """initialize PyShell object"""
        super(PyShell, self).__init__()
        self.intro = '==== Welcome to PyShell ===='
        self.prompt = f'{getpass.getuser()}@{socket.gethostname()}:{os.getcwd().replace(os.environ["HOME"], "~")}$ '
        self.background_jobs = []

    def preloop(self):
        super(PyShell, self).preloop()
        while True:
            try:
                os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break

    def cmdloop(self, intro=None):
        while True:
            try:
                super(PyShell, self).cmdloop()
            except KeyboardInterrupt:
                print()
                self.intro = ''
                continue

    def do_fg(self, arg_str: str) -> None:
        """usage: fg [pid]
        bring the most recent background job to foreground"""
        if len(self.background_jobs) == 0:
            print('fg: no background job running')
            return
        if len(arg_str) > 0:
            args = arg_str.split(' ')
            if len(args) > 1:
                print('fg: too many arguments', file=sys.stderr)
                return
            try:
                os.waitpid(int(args[0]), 0)
            except ValueError:
                print('fg: invalid pid', file=sys.stderr)
                return
        else:
            for pid in self.background_jobs[-1]:
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass
            self.background_jobs.pop()

    def do_jobs(self, arg_str: str) -> None:
        """usage: jobs
        list all background jobs"""
        if len(arg_str) > 0:
            print('jobs: too many arguments', file=sys.stderr)
            return
        for i in range(len(self.background_jobs)):
            print(f'[{i}] pid(s): {self.background_jobs[i]}', file=sys.stderr)

    def do_exit(self, arg_str: str) -> None:
        """usage: exit [exitcode]"""
        args = arg_str.split(' ')
        if len(args) > 1:
            print('exit: too many arguments', file=sys.stderr)
            return
        if args[0] == '':
            exit(0)
        try:
            exit(int(args[0]))
        except ValueError:
            print('exit: invalid exit code', file=sys.stderr)

    def do_cd(self, arg_str: str) -> None:
        """usage: cd target_path"""
        args = arg_str.split(' ')
        if len(args) > 1:
            print('cd: too many arguments', file=sys.stderr)
            return
        try:
            if args[0] == '':
                os.chdir(os.environ['HOME'])
            else:
                os.chdir(args[0].replace('~', os.environ['HOME']))
        except FileNotFoundError:
            print('cd: invalid path', file=sys.stderr)
        except NotADirectoryError:
            print('cd: not a directory', file=sys.stderr)
        else:
            self.prompt = f'{getpass.getuser()}@{socket.gethostname()}:{os.getcwd().replace(os.environ["HOME"], "~")}$ '

    def do_EOF(self, _: str) -> None:
        """EOF handler; equivalent to type exit"""
        print()
        exit(0)

    def default(self, line: str) -> None:
        """handler for undocumented inputs"""
        commands = shlex.split(line)

        self.main_function(
            [list(command)
             for is_pipe_operator, command in itertools.groupby(commands, lambda word: word == '|')
             if not is_pipe_operator],
            '&' not in commands
        )

    def main_function(self, args_list: [[str]], is_foreground=True) -> None:
        """handler for multiple piping"""
        children_pids = []
        new_fds, old_fds = [], []

        if not is_foreground:
            args_list[-1].pop()

        def _clean_up(error: OSError) -> None:
            map(lambda _pid: os.kill(_pid, signal.SIGKILL), children_pids)
            print(f'{args_list[i][0]}: {error}', file=sys.stderr)

        pid = -1

        try:
            for i in range(len(args_list)):
                if i < len(args_list) - 1:  # if there is a next cmd
                    new_fds = os.pipe()

                pid = os.fork()
                if pid == 0:
                    redirect_result, args_list[i] = PyShell.redirection_handler(args_list[i])

                    if i < len(args_list) - 1:  # if there is a next cmd
                        os.close(new_fds[0])
                        os.dup2(new_fds[1], sys.stdout.fileno())
                        os.close(new_fds[1])

                        if redirect_result[sys.stdout.fileno()] is True:
                            raise OSError('invalid usage of redirection and (or) piping')

                    if i > 0:  # if there is a previous cmd
                        os.dup2(old_fds[0], sys.stdin.fileno())
                        os.close(old_fds[0])
                        os.close(old_fds[1])

                        if redirect_result[sys.stdin.fileno()] is True:
                            raise OSError('invalid usage of redirection and (or) piping')

                    os.execvp(args_list[i][0], args_list[i])

                else:
                    children_pids.append(pid)
                    if i > 0:
                        os.close(old_fds[0])
                        os.close(old_fds[1])
                    if i < len(args_list) - 1:
                        old_fds = new_fds

            if is_foreground:
                try:
                    for i in children_pids:
                        os.waitpid(i, 0)
                except ChildProcessError:
                    pass
            else:
                self.background_jobs.append(children_pids)
                print(f'[{len(self.background_jobs) - 1}] new job added')

        except OSError as e:
            _clean_up(e)
            if pid == 0:
                exit(1)
            else:
                return

    @staticmethod
    def redirection_handler(args_with_redirection: [str]) -> ((bool, bool, bool), [str]):
        """handler for io redirection
        index is true when corresponding (IN, OUT, ERR) redirected
        also returns modified args (redirection operation removed)"""
        args_with_redirection = list(args_with_redirection)
        is_redirected = [False, False, False]
        if '<' in args_with_redirection:
            if not is_redirected[sys.stdin.fileno()]:
                is_redirected[sys.stdin.fileno()] = True

                file_path = args_with_redirection[args_with_redirection.index('<') + 1]

                if args_with_redirection.index('<') + 1 < len(args_with_redirection):
                    args_with_redirection.pop(args_with_redirection.index('<') + 1)
                    args_with_redirection.pop(args_with_redirection.index('<'))
                else:
                    raise OSError('invalid usage of redirection and (or) piping')

                fd = os.open(file_path, os.O_RDONLY, 0o644)
                os.dup2(fd, sys.stdin.fileno())
                os.close(fd)
            else:
                raise OSError('invalid usage of redirection and (or) piping')
        if '>' in args_with_redirection:
            if not is_redirected[sys.stdout.fileno()]:
                is_redirected[sys.stdout.fileno()] = True

                file_path = args_with_redirection[args_with_redirection.index('>') + 1]

                if args_with_redirection.index('>') + 1 < len(args_with_redirection):
                    args_with_redirection.pop(args_with_redirection.index('>') + 1)
                    args_with_redirection.pop(args_with_redirection.index('>'))
                else:
                    raise OSError('invalid usage of redirection and (or) piping')

                fd = os.open(file_path, os.O_WRONLY | os.O_CREAT, 0o644)
                os.dup2(fd, sys.stdout.fileno())
                os.close(fd)
            else:
                raise OSError('invalid usage of redirection and (or) piping')
        if '2>' in args_with_redirection:
            if not is_redirected[sys.stderr.fileno()]:
                is_redirected[sys.stderr.fileno()] = True

                file_path = args_with_redirection[args_with_redirection.index('2>') + 1]

                if args_with_redirection.index('2>') + 1 < len(args_with_redirection):
                    args_with_redirection.pop(args_with_redirection.index('2>') + 1)
                    args_with_redirection.pop(args_with_redirection.index('2>'))
                else:
                    raise OSError('invalid usage of redirection and (or) piping')

                fd = os.open(file_path, os.O_WRONLY | os.O_CREAT, 0o644)
                os.dup2(fd, sys.stderr.fileno())
                os.close(fd)
            else:
                raise OSError('invalid usage of redirection and (or) piping')
        if '>>' in args_with_redirection:
            if not is_redirected[sys.stdout.fileno()]:
                is_redirected[sys.stdout.fileno()] = True

                file_path = args_with_redirection[args_with_redirection.index('>>') + 1]

                if args_with_redirection.index('>>') + 1 < len(args_with_redirection):
                    args_with_redirection.pop(args_with_redirection.index('>>') + 1)
                    args_with_redirection.pop(args_with_redirection.index('>>'))
                else:
                    raise OSError('invalid usage of redirection and (or) piping')

                fd = os.open(file_path, os.O_APPEND | os.O_WRONLY | os.O_CREAT, 0o644)
                os.dup2(fd, sys.stdout.fileno())
                os.close(fd)
            else:
                raise OSError('invalid usage of redirection and (or) piping')
        if '2>>' in args_with_redirection:
            if not is_redirected[sys.stderr.fileno()]:
                is_redirected[sys.stderr.fileno()] = True

                file_path = args_with_redirection[args_with_redirection.index('2>>') + 1]

                if args_with_redirection.index('2>>') + 1 < len(args_with_redirection):
                    args_with_redirection.pop(args_with_redirection.index('2>>') + 1)
                    args_with_redirection.pop(args_with_redirection.index('2>>'))
                else:
                    raise OSError('invalid usage of redirection and (or) piping')

                fd = os.open(file_path, os.O_APPEND | os.O_WRONLY | os.O_CREAT, 0o644)
                os.dup2(fd, sys.stderr.fileno())
                os.close(fd)
            else:
                raise OSError('invalid usage of redirection and (or) piping')
        if '&>' in args_with_redirection:
            if not is_redirected[sys.stdout.fileno()] and not is_redirected[sys.stderr.fileno()]:
                is_redirected[sys.stdout.fileno()] = True
                is_redirected[sys.stderr.fileno()] = True

                file_path = args_with_redirection[args_with_redirection.index('&>') + 1]

                if args_with_redirection.index('&>') + 1 < len(args_with_redirection):
                    args_with_redirection.pop(args_with_redirection.index('&>') + 1)
                    args_with_redirection.pop(args_with_redirection.index('&>'))
                else:
                    raise OSError('invalid usage of redirection and (or) piping')

                fd = os.open(file_path, os.O_WRONLY | os.O_CREAT, 0o644)
                os.dup2(fd, sys.stderr.fileno())
                os.dup2(fd, sys.stdout.fileno())
                os.close(fd)
            else:
                raise OSError('invalid usage of redirection and (or) piping')
        return tuple(is_redirected), args_with_redirection


if __name__ == '__main__':
    PyShell().cmdloop()
