import nextcord as _nextcord
import os as _os

def get_command(data: dict) -> str:
    """
    Returns the command string from a slash command data
    
    Parameters
    ----------
    data: :class:`dict`
        The data of the slash command, from :attr:`Interaction.data`
    
    Returns
    -------
    :class:`str`
        The command string
    """
    res = data.get("name", "")
    if "options" in data:
        for option in data["options"]:
            res += " " + get_command(option)
    if "value" in data:
        res += ":" + str(data["value"])
    return res


def file_to_module(root: str, filepath: str) -> str:
    """
    Converts a filepath to a module path
    
    Parameters
    ----------
    root: :class:`str`
        The root directory
    \n
    filepath: :class:`str`
        The filepath to convert
        
    Returns
    -------
    :class:`str`
        The module path
    """
    return _os.path.join(root, filepath).removesuffix(".py").replace("src\\", "").replace("\\", ".").replace("/", ".")


def module_to_file(filepath: str) -> str:
    """
    Converts a module path to a filepath
    
    Parameters
    ----------
    filepath: :class:`str`
        The module path to convert
        
    Returns
    -------
    :class:`str`
        The filepath
    """
    return f"src.{filepath}".replace(".", _os.sep) + ".py"


def get_cogs() -> set[str]:
    """
    Returns a set of all the cogs
    
    Returns
    -------
    :class:`set[str]`
        The set of all the cogs
    """
    paths: list[str] = [
        "src\\commands",
        "src\\jobs",
        "src\\events"
    ]
    
    cogs = set()
    for path in paths:
        for root, dirs, files in _os.walk(path):
            if not root.startswith("__"):
                for file in files:
                    if file.endswith(".py"):
                        cogs.add(file_to_module(root, file))
                        
    return cogs


