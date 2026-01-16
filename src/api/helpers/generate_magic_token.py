from cuid2 import Cuid

CUID_GENERATOR: Cuid = Cuid(length=42)

def generate_magic_token():
    """
        Generate a MagicToken for User to Login
    """
    
    return CUID_GENERATOR.generate()
    