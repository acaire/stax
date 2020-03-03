"""
Stax CLI

Manage everything to do with Cloudformation
"""
import click
import json
import os


class Context:
    """
    Pass a context to all CLI commands
    and also retrieve it from custom classes
    so that we can use a uniform debug/config
    interface.
    """
    def __init__(self, debug):
        self._debug = debug
        self.config = self.get_config()

    def get_config(self):
        with open('stax.json', 'r') as fh:
            return json.load(fh)

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
            for filename in os.listdir(cmd_path)
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


@click.command(cls=CLI)
@click.version_option(version="0.1.0")
@click.option("--debug", is_flag=True)
@click.pass_context
def cli(ctx, debug):
    """
    Pystacks - Manage your Cloudformation Stacks
    """
    ctx.obj = Context(debug)


if __name__ == "__main__":
    cli()
