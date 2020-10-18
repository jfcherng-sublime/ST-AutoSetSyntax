class Globals(object):
    """
    @brief This class stores application-level global variables.
    """

    # the logger object
    logger = None  # type: Optional[logging.Logger]

    # the SyntaxMappings object
    syntax_mappings = None  # type: Optional[SyntaxMappings]

    working_scope_regex_obj = None  # type: Optional[Pattern]
