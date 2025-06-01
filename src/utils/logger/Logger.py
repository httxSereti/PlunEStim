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

    def log(message, removeEnd=False):
        formatedMessage = f"[{Colors.PURPLE}{getTime()}{Colors.RESET}] {message}{Colors.RESET}"

        if removeEnd:
            print(f"\r{formatedMessage}", end="")
        else:
            print(formatedMessage)

    def info(message, removeEnd=False):
        Logger.log(f"{Colors.BLUE}{message}", removeEnd=removeEnd)

    def error(message, removeEnd=False):
        Logger.log(f"{Colors.RED}{message}", removeEnd=removeEnd)
        
    def success(message, removeEnd=False):
        Logger.log(f"{Colors.GREEN}{message}", removeEnd=removeEnd)

    def warning(message, removeEnd=False):
        Logger.log(f"{Colors.YELLOW}{message}", removeEnd=removeEnd)

    def formatForInput(message, color=Colors.BLUE):
        formatedMessage = f"[{Colors.PURPLE}{getTime()}{Colors.RESET}] {color}{message}{Colors.RESET}"
        return formatedMessage