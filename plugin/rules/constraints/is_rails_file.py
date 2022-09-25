# modified from https://github.com/facelessuser/ApplySyntax/blob/master/as_plugins/is_rails_file.py

from typing import final

import sublime

from ..constraint import AbstractConstraint

RUBY_EXTENSIONS = (".rb", ".rake")


@final
class IsRailsFileConstraint(AbstractConstraint):
    """Check file location and name to determine if a Rails file."""

    def test(self, view: sublime.View) -> bool:
        view_info = self.get_view_info(view)

        # early return so that we may save some IO operations
        if not view_info["file_name"].lower().endswith(RUBY_EXTENSIONS):
            return False

        # I doubt this is the most elegant way of identifying a Rails directory structure,
        # but it does work. The idea here is to work up the tree, checking at each level for
        # the existence of "config/routes.rb". If it's found, the assumption is made that it's
        # a Rails app.
        return self.has_sibling(view_info["file_path"], "config/routes.rb", till_root=True)