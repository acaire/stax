"""
Stax CLI

Manage everything to do with Cloudformation
"""
import click
import json
import os
import sys

from stax import __version__


class Context:
    """
    Pass a context to all CLI commands
    and also retrieve it from custom classes
    so that we can use a uniform debug/config
    interface.
    """
    def __init__(self, debug):
        self._debug = debug
        self._config = None

    @property
    def config(self):
        if not self._config:
            self._config = self.get_config()
        return self._config

    def get_config(self):
        try:
            with open('stax.json', 'r') as fh:
                return json.load(fh)
        except json.decoder.JSONDecodeError as err:
            click.echo(click.style('Error decoding stacks.json: ', bold=True) +
                       str(err),
                       err=True)
            sys.exit(1)
        except FileNotFoundError:
            click.echo(
                click.style('stax.json not found', bold=True) +
                ' - Run "stax generate > stax.json" to generate a sample')
            sys.exit(1)

    def debug(self, msg):
        if self._debug:
            click.echo(f'debug: {msg}', err=True)


# Retrieve root commands from this path
cmd_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'commands'))


class CLI(click.MultiCommand):
    """
    This class loads commands automatically
    """
    def list_commands(self, ctx):
        """
        Find files in commands/ and return the base filenames
        to use as commands to the app
        """
        return [
            os.path.splitext(filename)[0][4:]
            for filename in sorted(os.listdir(cmd_path))
            if filename.endswith('.py') and filename.startswith('cmd_')
        ]

    def get_command(self, ctx, name):
        """
        Import found files as modules
        """
        try:
            mod_path = f'stax.commands.cmd_{name}'
            mod = __import__(mod_path, None, None, [name])
            return getattr(mod, name)
        except AttributeError:
            raise Exception(
                f'Please check {mod_path} ({cmd_path}/{name}.py), you need to define a function named {name}'
            )
        except ModuleNotFoundError:
            pass


@click.command(cls=CLI)
@click.version_option(version=__version__)
@click.option("--debug", is_flag=True)
@click.pass_context
def cli(ctx, debug):
    """
    Pystacks - Manage your Cloudformation Stacks
    """
    ctx.obj = Context(debug)


if __name__ == "__main__":
    cli()
