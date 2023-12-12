def removeprefix(text, prefix):
    """Backport of python 3.9 str.removeprefix"""

    if text.startswith(prefix):
        return text[len(prefix):]
    return text
