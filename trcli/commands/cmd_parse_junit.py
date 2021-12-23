import click
from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS
from trcli.readers.junit_xml import JunitParser
from trcli.api.results_uploader import ResultsUploader


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-f", "--file", type=click.Path(), help="Filename and path.")
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, file):
    environment.set_parameters(context)
    environment.check_for_required_parameters()
    result_uploader = ResultsUploader(
        environment=environment, result_file_parser=JunitParser(environment.file)
    )
    result_uploader.upload_results()
