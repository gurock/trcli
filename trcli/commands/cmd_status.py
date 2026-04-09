from requests.models import PreparedRequest, InvalidURL, MissingSchema

import click

import trcli
from click.core import ParameterSource

from trcli.api.api_client import APIClient
from trcli.api.api_request_handler import ApiRequestHandler
from trcli.cli import CONTEXT_SETTINGS, Environment, pass_environment
from trcli.cli_styles import StyledCommand, style_text
from trcli.commands.results_parser_helpers import build_command_json, json_output_option
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.version_checker import _query_pypi


def _build_api_client(environment: Environment) -> APIClient:
    api_client = APIClient(
        environment.host,
        verbose_logging_function=environment.vlog,
        logging_function=environment.log,
        verify=not environment.insecure,
        proxy=environment.proxy,
        proxy_user=environment.proxy_user,
        noproxy=environment.noproxy,
        uploader_metadata=APIClient.build_uploader_metadata(version=trcli.__version__),
        timeout=environment.timeout,
        dry_run=bool(getattr(environment, "dry_run", False)),
    )
    api_client.username = environment.username
    api_client.password = environment.password
    api_client.api_key = environment.key
    return api_client


def _auth_mode(environment: Environment) -> str:
    if environment.username and environment.key:
        return "username + API key"
    if environment.username and environment.password:
        return "username + password"
    if environment.username or environment.password or environment.key:
        return "incomplete"
    return "not configured"


def _validate_host(host: str) -> bool:
    if not host:
        return False
    try:
        request = PreparedRequest()
        request.prepare_url(host, params=None)
        return True
    except (InvalidURL, MissingSchema):
        return False


def _resolved_parameter_sources(environment: Environment, context: click.Context) -> dict:
    resolved_sources = {}
    config_override_sources = [ParameterSource.DEFAULT] if environment.default_config_file else [
        ParameterSource.DEFAULT,
        ParameterSource.ENVIRONMENT,
    ]

    for current_context in [context.parent, context]:
        if not current_context:
            continue
        for param in current_context.params:
            if param == "config":
                continue
            source = current_context.get_parameter_source(param)
            if source is None:
                continue
            if source in config_override_sources and environment.params_from_config.get(param) is not None:
                resolved_sources[param] = "config file"
            elif source == ParameterSource.COMMANDLINE:
                resolved_sources[param] = "command line"
            elif source == ParameterSource.ENVIRONMENT:
                resolved_sources[param] = "environment variable"
            elif source == ParameterSource.DEFAULT:
                resolved_sources[param] = "default"

    return resolved_sources


def _format_source_summary(source_map: dict) -> str:
    ordered = []
    labels = ["command line", "environment variable", "config file", "default"]
    if any(label in source_map.values() for label in labels[:-1]):
        labels = labels[:-1]
    for label in labels:
        if label in source_map.values():
            ordered.append(label)
    return " + ".join(ordered) if ordered else "default"


def _print_section(environment: Environment, title: str, rows: list[tuple[str, str]]):
    ctx = click.get_current_context(silent=True)
    environment.log(style_text(f"{title}:", "accent", ctx=ctx))
    for key, value in rows:
        environment.log(
            f"  {style_text(key + ':', 'muted', ctx=ctx)} {style_text(value, 'muted', ctx=ctx)}"
        )
    environment.log("")


def _render_status_heading(environment: Environment, verdict: str):
    ctx = click.get_current_context(silent=True)
    verdict_color = {"Ready": "success", "Partial": "warn", "Error": "error"}[verdict]
    environment.log(
        f"{style_text('TRCLI Status:', 'accent', ctx=ctx)} {style_text(verdict, verdict_color, ctx=ctx)}"
    )
    environment.log("")


def _render_message_block(environment: Environment, title: str, items: list[str], color: str):
    if not items:
        return

    ctx = click.get_current_context(silent=True)
    environment.log(style_text(f"{title}:", color, ctx=ctx))
    for item in items:
        environment.log(f"  {style_text('-', color, ctx=ctx)} {style_text(item, 'muted', ctx=ctx)}")
    environment.log("")


@click.command(cls=StyledCommand, context_settings=CONTEXT_SETTINGS)
@json_output_option
@click.option(
    "--suite-id",
    type=click.IntRange(min=1),
    metavar="",
    help="Optional suite ID to validate within the selected project.",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, suite_id: int, *args, **kwargs):
    """Show TRCLI configuration and connectivity status"""
    environment.cmd = "status"
    environment.set_parameters(context)

    source_map = _resolved_parameter_sources(environment, context)
    status_data = {
        "version": {
            "installed": trcli.__version__,
            "latest": _query_pypi() or "unavailable",
        },
        "config": {
            "source": _format_source_summary(source_map),
            "config_file": str(environment.config) if environment.config else "not used",
            "proxy": environment.proxy or "disabled",
            "proxy_user": "configured" if environment.proxy_user else "not configured",
            "noproxy": environment.noproxy or "not configured",
            "insecure_ssl": "yes" if environment.insecure else "no",
            "timeout": str(environment.timeout),
            "batch_size": str(environment.batch_size),
        },
        "connection": {
            "host": environment.host or "not configured",
            "auth": _auth_mode(environment),
            "reachable": "not checked",
            "authentication": "not checked",
        },
        "context": {
            "project": environment.project or "not configured",
            "project_id": str(environment.project_id) if environment.project_id else "not configured",
            "suite_id": str(environment.suite_id) if environment.suite_id else "not configured",
            "project_check": "not checked",
            "suite_check": "not checked",
        },
    }

    warnings = []
    errors = []

    host_is_valid = _validate_host(environment.host)
    if not environment.host:
        warnings.append("Host is not configured.")
    elif not host_is_valid:
        errors.append("Host is invalid.")

    auth_mode = status_data["connection"]["auth"]
    if auth_mode == "not configured":
        warnings.append("Authentication is not configured.")
    elif auth_mode == "incomplete":
        errors.append("Authentication configuration is incomplete.")

    api_handler = None
    project_id = None

    if host_is_valid and auth_mode not in ["not configured", "incomplete"]:
        api_client = _build_api_client(environment)
        connectivity = api_client.send_get("get_projects")
        if connectivity.status_code != -1 and 200 <= connectivity.status_code < 300 and not connectivity.error_message:
            status_data["connection"]["reachable"] = "yes"
            status_data["connection"]["authentication"] = "valid"
            api_handler = ApiRequestHandler(
                environment=environment,
                api_client=api_client,
                suites_data=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
                verify=False,
            )
        else:
            status_data["connection"]["reachable"] = "no"
            status_data["connection"]["authentication"] = "failed"
            message = connectivity.error_message or f"HTTP {connectivity.status_code}"
            errors.append(f"Connectivity/authentication check failed: {message}")

    if environment.project:
        if api_handler is None:
            status_data["context"]["project_check"] = "skipped"
        else:
            project_data = api_handler.get_project_data(environment.project, environment.project_id)
            if project_data.project_id > 0:
                project_id = project_data.project_id
                status_data["context"]["project_id"] = str(project_id)
                status_data["context"]["project_check"] = "valid"
            else:
                status_data["context"]["project_check"] = "invalid"
                errors.append(project_data.error_message)
    else:
        warnings.append("Project is not configured.")

    if environment.suite_id:
        if project_id is None or api_handler is None:
            status_data["context"]["suite_check"] = "skipped"
            warnings.append("Suite ID is configured but could not be validated without a valid project context.")
        else:
            suite_exists, error_message = api_handler.check_suite_id(project_id)
            if suite_exists:
                status_data["context"]["suite_check"] = "valid"
            else:
                status_data["context"]["suite_check"] = "invalid"
                errors.append(error_message)

    if errors:
        verdict = "Error"
    elif warnings:
        verdict = "Partial"
    else:
        verdict = "Ready"

    if environment.wants_json_output:
        data = {
            "verdict": verdict,
            **status_data,
        }
        if environment.verbose:
            data["parameter_sources"] = source_map
        environment.emit_json(
            build_command_json(
                "status",
                ok=verdict != "Error",
                dry_run=bool(getattr(environment, "dry_run", False)),
                data=data,
                warnings=warnings,
                errors=errors,
            )
        )
        if verdict == "Error":
            exit(1)
        return

    _render_status_heading(environment, verdict)
    _print_section(
        environment,
        "Connection",
        [
            ("Host", status_data["connection"]["host"]),
            ("Auth", status_data["connection"]["auth"]),
            ("Reachable", status_data["connection"]["reachable"]),
            ("Authentication", status_data["connection"]["authentication"]),
        ],
    )
    _print_section(
        environment,
        "Context",
        [
            ("Project", status_data["context"]["project"]),
            ("Project ID", status_data["context"]["project_id"]),
            ("Project Check", status_data["context"]["project_check"]),
            ("Suite ID", status_data["context"]["suite_id"]),
            ("Suite Check", status_data["context"]["suite_check"]),
        ],
    )
    _print_section(
        environment,
        "Config",
        [
            ("Source", status_data["config"]["source"]),
            ("Config File", status_data["config"]["config_file"]),
            ("Proxy", status_data["config"]["proxy"]),
            ("Proxy User", status_data["config"]["proxy_user"]),
            ("No Proxy", status_data["config"]["noproxy"]),
            ("Insecure SSL", status_data["config"]["insecure_ssl"]),
            ("Timeout", status_data["config"]["timeout"]),
            ("Batch Size", status_data["config"]["batch_size"]),
        ],
    )
    _print_section(
        environment,
        "Version",
        [
            ("Installed", status_data["version"]["installed"]),
            ("Latest", status_data["version"]["latest"]),
        ],
    )

    _render_message_block(environment, "Warnings", warnings, "warn")
    _render_message_block(environment, "Errors", errors, "error")

    if environment.verbose:
        ctx = click.get_current_context(silent=True)
        environment.log(style_text("Verbose:", "accent", ctx=ctx))
        environment.log(f"  {style_text('Resolved parameter sources:', 'muted', ctx=ctx)}")
        for key in sorted(source_map):
            environment.log(
                f"    {style_text(key + ':', 'muted', ctx=ctx)} {style_text(source_map[key], 'muted', ctx=ctx)}"
            )
        environment.log("")

    if verdict == "Error":
        exit(1)
