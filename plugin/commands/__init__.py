from .auto_set_syntax import AutoSetSyntaxCommand, run_auto_set_syntax_on_view
from .auto_set_syntax_create_new_implementation import (
    AutoSetSyntaxCreateNewConstraintCommand,
    AutoSetSyntaxCreateNewMatchCommand,
)
from .auto_set_syntax_debug_information import AutoSetSyntaxDebugInformationCommand
from .auto_set_syntax_download_dependencies import AutoSetSyntaxDownloadDependenciesCommand
from .auto_set_syntax_download_guesslang_server import AutoSetSyntaxDownloadGuesslangServerCommand
from .auto_set_syntax_restart_guesslang import AutoSetSyntaxRestartGuesslangCommand

__all__ = (
    # ST: commands
    "AutoSetSyntaxCommand",
    "AutoSetSyntaxCreateNewConstraintCommand",
    "AutoSetSyntaxCreateNewMatchCommand",
    "AutoSetSyntaxDebugInformationCommand",
    "AutoSetSyntaxDownloadDependenciesCommand",
    "AutoSetSyntaxDownloadGuesslangServerCommand",
    "AutoSetSyntaxRestartGuesslangCommand",
    # ...
    "run_auto_set_syntax_on_view",
)
