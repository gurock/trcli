import inspect
import os
import re
import sys

import click
from click import _compat


LOBSTER_PALETTE = {
    "accent": "33",
    "accent_bright": "93",
    "accent_dim": "33",
    "info": "93",
    "success": "32",
    "warn": "33",
    "error": "31",
    "muted": "37",
}


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def should_color(ctx: click.Context | None) -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if ctx is None:
        return False
    return not _compat.should_strip_ansi(sys.stdout, getattr(ctx, "color", None))


def style_text(
    text: str,
    color_name: str,
    *,
    ctx: click.Context | None = None,
    bold: bool = False,
    dim: bool = False,
) -> str:
    if not should_color(ctx):
        return text

    codes = [LOBSTER_PALETTE[color_name]]
    if dim:
        codes.append("2")
    return f"\033[{';'.join(codes)}m{text}\033[0m"


class StyledHelpMixin:
    command_class = None
    group_class = None

    @staticmethod
    def _style_usage_piece(ctx: click.Context, piece: str) -> str:
        if not piece:
            return piece
        if piece.startswith("-") or piece.startswith("[") or piece.startswith("<"):
            return style_text(piece, "muted", ctx=ctx, bold=True)
        if piece.isupper():
            return style_text(piece, "muted", ctx=ctx, bold=True)
        return style_text(piece, "accent_bright", ctx=ctx, bold=True)

    def collect_usage_pieces(self, ctx: click.Context) -> list[str]:
        return [self._style_usage_piece(ctx, piece) for piece in super().collect_usage_pieces(ctx)]

    def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        pieces = self.collect_usage_pieces(ctx)
        formatter.write_usage(
            style_text(ctx.command_path, "accent_bright", ctx=ctx, bold=True),
            " ".join(pieces),
            prefix=style_text("Usage: ", "accent", ctx=ctx, bold=True),
        )

    def format_help_text(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        if self.help:
            formatter.write_paragraph()
            formatter.write_text(style_text(self.help, "muted", ctx=ctx))
            formatter.write_paragraph()

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        records = []
        for param in self.get_params(ctx):
            record = param.get_help_record(ctx)
            if record is None:
                continue
            option, help_text = record
            records.append(
                (
                    style_text(option, "accent_bright", ctx=ctx, bold=True),
                    style_text(help_text, "muted", ctx=ctx),
                )
            )

        if records:
            with formatter.section(style_text("Options", "accent", ctx=ctx, bold=True)):
                formatter.write_dl(records)

        if isinstance(self, click.MultiCommand):
            self.format_commands(ctx, formatter)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None or cmd.hidden:
                continue
            commands.append(
                (
                    style_text(subcommand, "accent_bright", ctx=ctx, bold=True),
                    style_text(cmd.get_short_help_str(), "muted", ctx=ctx),
                )
            )

        if commands:
            with formatter.section(style_text("Commands", "accent", ctx=ctx, bold=True)):
                formatter.write_dl(commands)

    def format_epilog(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        if not self.epilog:
            return

        formatter.write_paragraph()
        lines = inspect.cleandoc(self.epilog).splitlines()
        in_examples = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                formatter.write("\n")
                continue

            if stripped == "Examples:":
                in_examples = True
                formatter.write(f"{style_text('Examples:', 'accent', ctx=ctx, bold=True)}\n")
                continue

            if stripped.startswith("Docs:"):
                in_examples = False
                label, url = stripped.split(":", 1)
                formatter.write("\n")
                formatter.write(
                    f"{style_text(label + ':', 'muted', ctx=ctx)} {style_text(url.strip(), 'accent_bright', ctx=ctx)}\n"
                )
                continue

            leading_spaces = len(line) - len(line.lstrip(" "))
            indent = " " * leading_spaces

            if in_examples:
                color = "accent_bright" if leading_spaces <= 2 else "muted"
                formatter.write(f"{indent}{style_text(stripped, color, ctx=ctx)}\n")
                continue

            formatter.write(f"{indent}{style_text(stripped, 'muted', ctx=ctx)}\n")


class StyledCommand(StyledHelpMixin, click.Command):
    pass


class StyledGroup(StyledHelpMixin, click.Group):
    command_class = StyledCommand
    group_class = None


StyledGroup.group_class = StyledGroup
