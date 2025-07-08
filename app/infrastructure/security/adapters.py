import bcrypt

from app.application.ports.services import PasswordHasher, PasswordVerifier
from app.domain.value_objects import UserPasswordHash, UserRawPassword

class BcryptHasher(PasswordHasher):
    def hash(self, raw_password: UserRawPassword) -> UserPasswordHash:
        return UserPasswordHash(bcrypt.hashpw(raw_password.value.encode(), bcrypt.gensalt()))

class BcryptPasswordVerifier(PasswordVerifier):
    def verify(self, raw_password: UserRawPassword, hashed_password: UserPasswordHash) -> bool:
        """Return True if raw_password matches the hashed_password."""
        return bcrypt.checkpw(raw_password.value.encode(), hashed_password.value)