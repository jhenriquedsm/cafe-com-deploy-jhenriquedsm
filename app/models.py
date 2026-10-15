from sqlalchemy import Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Cafe(Base):
    __tablename__ = "cafes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True)
    preco: Mapped[float] = mapped_column(Numeric(6, 2, asdecimal=False))