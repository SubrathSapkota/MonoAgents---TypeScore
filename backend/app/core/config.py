import os

SECRET_KEY: str = os.getenv("SECRET_KEY", "typescore-hackathon-secret-2026")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql+aiomysql://root@localhost/hackathon?charset=utf8mb4",
)
