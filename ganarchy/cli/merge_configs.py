import pathlib

import click

import ganarchy
import ganarchy.cli
import ganarchy.data

@ganarchy.cli.main.command()
@click.option('--skip-errors/--no-skip-errors', default=False)
@click.argument('files', type=click.Path(exists=True, dir_okay=False, resolve_path=True), nargs=-1)
def merge_configs(skip_errors, files):
    """Merges config files."""
    configs = [ganarchy.data.LocalDataSource(filename) for filename in files]
    rlm = ganarchy.data.RepoListManager(ganarchy.data.ObjectDataSource({}))
    rlm.sources += configs
    res = []
    for src in rlm.sources:
        res.append(src.update())
    effective = ganarchy.data.EffectiveSource(rlm)
    if any(x is None for x in res):
        click.echo("# This is DEPRECATED and will be REMOVED at some point!")
        for pctp in effective.get_property_values(ganarchy.data.DataProperty.VCS_REPOS):
            if pctp.active:
                click.echo(f"""projects."{ganarchy.tomlescape(pctp.project_commit)}"."{ganarchy.tomlescape(pctp.uri)}"."{ganarchy.tomlescape(pctp.branch)}" = {{ active=true }}""")
