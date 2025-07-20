"""
Seed-script: creates the first super-user via CreateUserUseCase.

Usage:
    python seed_admin.py                    # default ENV: ADMIN_USERNAME / ADMIN_PASSWORD
    python seed_admin.py USER_ENV PW_ENV    # custom env var names
"""

# ── add CWD to import path ───────────────────────────────────────────────────
import os, sys, asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # …/<project-root>
if str(ROOT) not in sys.path:                       
    sys.path.insert(0, str(ROOT))
# ─────────────────────────────────────────────────────────────────────────────

# stdlib / typing
# sqlalchemy async engine / session
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# project imports
from app.config.config import settings
from app.infrastructure.security.adapters import BcryptHasher
from app.domain.value_objects import UserId, Username, UserRole, UserRawPassword
from app.domain.entities.user import User

from app.application.dto import CreateUserInputDTO, CreateUserOutputDTO, CredentialDTO
from app.application.use_cases.create_user import CreateUserUseCase
from app.application.ports.services import AuthService
from app.application.ports.presenters import AuthPresenter, State
from app.infrastructure.db.sqlalchemy.adapters import UoWSQL, UUIDv4Generator            
from app.domain.entities.user.repo import UserRepository
from app.application.ports.uow import UnitOfWork
from app.config import settings, APP_PREFIX

# ── simple CLI presenter ─────────────────────────────────────────────────────
class CLIPresenter(AuthPresenter[CreateUserOutputDTO]):                
    _state: State
    response: CreateUserOutputDTO|str

    def ok(self, dto: CreateUserOutputDTO) -> None:
        self._state, self.response = State.OK, dto

    def error(self, message: str) -> None:
        self._state, self.response = State.ERROR, message

    def conflict(self, message: str) -> None:
        self._state, self.response = State.CONFLICT, message

    def unauthorized(self, message: str) -> None:
        self._state, self.response = State.UNAUTHORIZED, message

    def forbidden(self, message: str) -> None:
        self._state, self.response = State.FORBIDDEN, message

    # ── property required by Protocol ────────────────────────────────────
    @property
    def state(self) -> State:
        return self._state

# ── fake AuthService for seeding (no real user) ──────────────────────────────
class SeederAuthService(AuthService[UserRepository]):
    def __init__(self, credentials: CredentialDTO) -> None:
        self.credentials = credentials

    async def current_user(self, repo: UserRepository) -> User:
        pwd_hash = BcryptHasher().hash(UserRawPassword("_seed_"))
        return User.create(
            username=Username("_seed_"),
            password_hash=pwd_hash,
            role=UserRole.ADMIN,
            id_gen=UUIDv4Generator(),
        )

    def ensure_role(
        self,
        user_id: UserId,
        role: UserRole,
        target_role: UserRole,
    ) -> None:
        return        
    
# ── build session-maker & UoW factory ───────────────────────────────────────-
engine = create_async_engine(str(settings.POSTGRES_URL), pool_pre_ping=True)
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)

def uow_factory() -> UnitOfWork:
    return UoWSQL(async_session)          # ← your UoW adapter

# ── main async logic ─────────────────────────────────────────────────────────
async def main() -> None:
    argc = len(sys.argv)                     # включает имя скрипта
    if argc == 1:                            # «python seed_admin.py»
        user_env = f"{APP_PREFIX}ADMIN_USERNAME"
        pass_env = f"{APP_PREFIX}ADMIN_PASSWORD"
    elif argc == 3:                          # «python seed_admin.py USER_ENV PW_ENV»
        user_env = sys.argv[1]
        pass_env = sys.argv[2]
    else:
        sys.exit("Usage: seed_admin.py [USERNAME_ENV_NAME] [PASSWORD_ENV_NAME]")

    username = os.getenv(user_env)
    password = os.getenv(pass_env)
    if not username or not password:
        sys.exit(f"ENV {user_env} / {pass_env} must be set")

    use_case = CreateUserUseCase(
        auth_service=SeederAuthService(credentials=CredentialDTO(scheme="apikey", value="some")),
        uow_factory=uow_factory,
        hasher=BcryptHasher(),
        id_gen=UUIDv4Generator(),
    )

    presenter = CLIPresenter()
    await use_case.execute(
        CreateUserInputDTO(username=username, password=password, role="admin"),
        presenter,
    )

    match presenter.state:
        case State.OK:
            dto = presenter.response
            assert isinstance(dto, CreateUserOutputDTO)
            print(f"✅ Admin created (id={dto.id}, user={dto.username})")
        case State.CONFLICT:
            print(f"⚠️  {presenter.response}")
        case _:
            print(f"❌ {presenter.response}")

if __name__ == "__main__":
    asyncio.run(main())
