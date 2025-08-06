from passlib.context import CryptContext
import secrets
import string


class PasswordUtils:
    
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        return cls.pwd_context.hash(password)
    
    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        return cls.pwd_context.verify(plain_password, hashed_password)
    
    @classmethod
    def needs_update(cls, hashed_password: str) -> bool:
        return cls.pwd_context.needs_update(hashed_password)
    
    @staticmethod
    def generate_random_password(length: int = 12) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        return password
    
    @staticmethod
    def generate_reset_token(length: int = 32) -> str:
        return secrets.token_urlsafe(length)