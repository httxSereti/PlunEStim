from datetime import datetime
class Colors:
	RED = "\033[91m"
	BLUE = "\033[94m"
	RESET = "\033[0m"
	GREEN = "\033[92m"
	PURPLE = "\033[35m"
	BLACK  = '\033[30m'
	YELLOW = '\033[33m'
	BEIGE  = '\033[36m'
	WHITE  = '\033[37m'
 
def getTime():
	return datetime.now().strftime("%H:%M:%S:%f")[:-3]

class Logger:
    """ Logger class to log into Console. """
    
    @staticmethod
    def log(
        message: str,
        removeEnd: bool = False
    ):
        """
        Log message into Console

        Parameters
        ----------
        message: :class:`str`
            The message to send.
        \n
        removeEnd: :class:`bool`
            Remove End of line.
        """
        formatedMessage = f"[{Colors.PURPLE}{getTime()}{Colors.RESET}] {message}{Colors.RESET}"

        if removeEnd:
            print(f"\r{formatedMessage}", end="")
        else:
            print(formatedMessage)

    @staticmethod
    def info(
        message: str,
        removeEnd: bool = False
    ):
        """
        Log message into Logger as INFO

        Parameters
        ----------
        message: :class:`str`
            The message to send.
        \n
        removeEnd: :class:`bool`
            Remove End of line.
        """
        Logger.log(f"{Colors.BLUE}{message}", removeEnd=removeEnd)

    @staticmethod
    def error(
        message: str,
        removeEnd: bool = False
    ):
        """
        Log message into Logger as ERROR

        Parameters
        ----------
        message: :class:`str`
            The message to send.
        \n
        removeEnd: :class:`bool`
            Remove End of line.
        """
        Logger.log(f"{Colors.RED}{message}", removeEnd=removeEnd)
        
    @staticmethod
    def success(
        message: str,
        removeEnd: bool = False
    ):
        """
        Log message into Logger as SUCCESS

        Parameters
        ----------
        message: :class:`str`
            The message to send.
        \n
        removeEnd: :class:`bool`
            Remove End of line.
        """
        Logger.log(f"{Colors.GREEN}{message}", removeEnd=removeEnd)

    @staticmethod
    def warning(
        message: str,
        removeEnd: bool = False
    ):
        """
        Log message into Logger as WARNING

        Parameters
        ----------
        message: :class:`str`
            The message to send.
        \n
        removeEnd: :class:`bool`
            Remove End of line.
        """
        Logger.log(f"{Colors.YELLOW}{message}", removeEnd=removeEnd)

    @staticmethod
    def formatMessage(
        message: str,
        color: str = Colors.BLUE
    ):
        """
        Format message as Logged Message

        Parameters
        ----------
        message: :class:`str`
            The message to format.
        \n
        color: :class:`str`
            Color to use.
        """
        formatedMessage = f"[{Colors.PURPLE}{getTime()}{Colors.RESET}] {color}{message}{Colors.RESET}"
        return formatedMessage