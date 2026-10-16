def test_health(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_version(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "abc1234")
    resposta = client.get("/version")
    assert resposta.status_code == 200
    assert resposta.json() == {"version": "abc1234"}


def test_criar_e_listar_cafes(client):
    criado = client.post("/cafes", json={"nome": "Espresso", "preco": 6.5})
    assert criado.status_code == 201
    assert criado.json()["nome"] == "Espresso"

    lista = client.get("/cafes")
    assert lista.status_code == 200
    assert [c["nome"] for c in lista.json()] == ["Espresso"]


def test_cafe_duplicado_retorna_409(client):
    client.post("/cafes", json={"nome": "Latte", "preco": 10})
    resposta = client.post("/cafes", json={"nome": "Latte", "preco": 12})
    assert resposta.status_code == 409


def test_cafe_inexistente_retorna_404(client):
    assert client.get("/cafes/999").status_code == 404


def test_preco_com_desconto_valido(client):
    cafe = client.post("/cafes", json={"nome": "Mocha", "preco": 10}).json()
    resposta = client.get(f"/cafes/{cafe['id']}/preco", params={"desconto": 10})
    assert resposta.status_code == 200
    assert resposta.json() == {"preco_final": 9.0}


def test_preco_com_desconto_invalido_retorna_422(client):
    cafe = client.post("/cafes", json={"nome": "Coado", "preco": 8}).json()
    resposta = client.get(f"/cafes/{cafe['id']}/preco", params={"desconto": 80})
    assert resposta.status_code == 422
    
def test_criar_cafe_com_origem(client):
    resposta = client.post(
        "/cafes", json={"nome": "Cerrado", "preco": 12, "origem": "Cerrado Mineiro"}
    )
    assert resposta.status_code == 201
    assert resposta.json()["origem"] == "Cerrado Mineiro"