import os
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Cafe

app = FastAPI(title="Café com Deploy")

DbSession = Annotated[Session, Depends(get_db)]


class CafeIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    preco: float = Field(gt=0)


def preco_com_desconto(preco: float, pct: float) -> float:
    """Regra de negócio: desconto entre 0% e o máximo configurado."""
    maximo = float(os.getenv("DESCONTO_MAXIMO", "50"))
    if not 0 <= pct <= maximo:
        raise ValueError("desconto inválido")
    return round(preco * (1 - pct / 100), 2)


def _saida(cafe: Cafe) -> dict:
    return {"id": cafe.id, "nome": cafe.nome, "preco": cafe.preco}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": os.getenv("APP_VERSION", "dev")}


@app.get("/cafes")
def listar_cafes(db: DbSession):
    return [_saida(c) for c in db.scalars(select(Cafe).order_by(Cafe.id))]


@app.post("/cafes", status_code=201)
def criar_cafe(dados: CafeIn, db: DbSession):
    cafe = Cafe(nome=dados.nome, preco=dados.preco)
    db.add(cafe)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="café já existe")
    db.refresh(cafe)
    return _saida(cafe)


@app.get("/cafes/{cafe_id}")
def obter_cafe(cafe_id: int, db: DbSession):
    cafe = db.get(Cafe, cafe_id)
    if not cafe:
        raise HTTPException(status_code=404, detail="café não encontrado")
    return _saida(cafe)


@app.get("/cafes/{cafe_id}/preco")
def preco_do_cafe(cafe_id: int, db: DbSession, desconto: float = 0):
    cafe = db.get(Cafe, cafe_id)
    if not cafe:
        raise HTTPException(status_code=404, detail="café não encontrado")
    try:
        return {"preco_final": preco_com_desconto(cafe.preco, desconto)}
    except ValueError:
        raise HTTPException(status_code=422, detail="desconto inválido")