import subprocess
from sys import stderr
import sys
from typing import Callable
from .core import Config
__all__ = [
	"run_command",
	"run_assembler"
]

def run_command(command:'list[str]', config:Config) -> int:
	if not config.silent:
		print(f"[CMD] {' '.join(command)}" )
	return subprocess.call(command)
def run_assembler(config:Config) -> None:
	if not config.run_assembler:
		return
	run:Callable[[list[str]], int] = lambda x:run_command(x, config)
	args = ['nasm', config.output_file+'.asm', '-f', 'elf64']
	if config.debug:
		args += ['-g', '-F', 'dwarf']
	ret_code = run(args)
	if ret_code != 0:
		print(f"ERROR: nasm exited abnormally with exit code {ret_code}", file=stderr)
		sys.exit(50)
	ret_code = run(['ld', '-o', config.output_file+'.out', config.output_file+'.o'])
	if ret_code != 0:
		print(f"ERROR: GNU linker exited abnormally with exit code {ret_code}", file=stderr)
		sys.exit(51)
	ret_code = run(['chmod', '+x', config.output_file+'.out'])
	if ret_code != 0:
		print(f"ERROR: chmod exited abnormally with exit code {ret_code}", file=stderr)
		sys.exit(52)
