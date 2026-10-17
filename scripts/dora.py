"""Métricas DORA calculadas a partir do histórico do GitHub.

Uso:
    python scripts/dora.py
    python scripts/dora.py --repo dono/repositorio --desde 2026-10-16

Só usa a biblioteca padrão. Sem token, a API do GitHub permite poucas
requisições por hora; se precisar, defina GITHUB_TOKEN no ambiente.
"""
import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

API = "https://api.github.com"
REPO_PADRAO = "jhenriquedsm/cafe-com-deploy-jhenriquedsm"
BRT = timezone(timedelta(hours=-3), "BRT")


def get(caminho):
    req = Request(API + caminho, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "dora-script",
    })
    token = os.getenv("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except HTTPError as erro:
        if erro.code == 403:
            sys.exit("Limite da API do GitHub atingido. Defina GITHUB_TOKEN e tente de novo.")
        raise


def agora(texto):
    return datetime.fromisoformat(texto)


def duracao(delta):
    segundos = int(delta.total_seconds())
    minutos, seg = divmod(segundos, 60)
    horas, minutos = divmod(minutos, 60)
    if horas:
        return f"{horas}h {minutos:02d}min"
    return f"{minutos}min {seg:02d}s"


def local(momento):
    return momento.astimezone(BRT).strftime("%d/%m %H:%M")


def execucoes(repo, workflow):
    caminho = f"/repos/{repo}/actions/workflows/{workflow}/runs?per_page=100"
    return get(caminho)["workflow_runs"]


def job(repo, run_id, nome):
    for item in get(f"/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100")["jobs"]:
        if item["name"] == nome:
            return item
    return None


def primeiro_commit(repo, run):
    """Data do primeiro commit do PR que originou o deploy (ou do próprio commit)."""
    achado = re.search(r"#(\d+)", run.get("display_title") or "")
    if achado:
        commits = get(f"/repos/{repo}/pulls/{achado.group(1)}/commits?per_page=100")
        if commits:
            return min(agora(c["commit"]["committer"]["date"]) for c in commits)
    commit = get(f"/repos/{repo}/commits/{run['head_sha']}")
    return agora(commit["commit"]["committer"]["date"])


def coletar_deploys(repo, desde):
    deploys = []
    for run in execucoes(repo, "cd.yml"):
        if run["event"] != "push" or run["head_branch"] != "main":
            continue
        producao = job(repo, run["id"], "production")
        if not producao or producao["conclusion"] not in ("success", "failure"):
            continue  # runs sem job de produção não são deploys
        fim = agora(producao["completed_at"])
        if desde and fim < desde:
            continue
        deploys.append({
            "numero": run["run_number"],
            "sha": run["head_sha"][:7],
            "ok": producao["conclusion"] == "success",
            "commit": primeiro_commit(repo, run),
            "push": agora(run["created_at"]),
            "fim": fim,
        })
    return sorted(deploys, key=lambda d: d["fim"])


def coletar_rollbacks(repo, desde):
    rollbacks = []
    for run in execucoes(repo, "rollback.yml"):
        if run["event"] != "workflow_dispatch":
            continue
        etapa = job(repo, run["id"], "rollback")
        if not etapa or etapa["conclusion"] != "success":
            continue
        inicio = agora(run["created_at"])
        if desde and inicio < desde:
            continue
        rollbacks.append({
            "numero": run["run_number"],
            "inicio": inicio,
            "fim": agora(etapa["completed_at"]),
        })
    return sorted(rollbacks, key=lambda r: r["inicio"])


def main():
    parser = argparse.ArgumentParser(description="Métricas DORA a partir do GitHub")
    parser.add_argument("--repo", default=REPO_PADRAO)
    parser.add_argument("--desde", help="considera só eventos a partir de AAAA-MM-DD (UTC)")
    args = parser.parse_args()
    desde = None
    if args.desde:
        desde = datetime.fromisoformat(args.desde).replace(tzinfo=UTC)

    deploys = coletar_deploys(args.repo, desde)
    rollbacks = coletar_rollbacks(args.repo, desde)
    if not deploys:
        sys.exit("Nenhum deploy em produção encontrado.")

    revertidos = set()
    for rb in rollbacks:
        anteriores = [d for d in deploys if d["fim"] <= rb["inicio"]]
        if anteriores:
            revertidos.add(anteriores[-1]["numero"])

    total = len(deploys)
    falhas_pipeline = sum(1 for d in deploys if not d["ok"])
    falhas = falhas_pipeline + len(revertidos - {d["numero"] for d in deploys if not d["ok"]})
    dias = max(1.0, (datetime.now(UTC) - deploys[0]["fim"]).total_seconds() / 86400)
    lead = [d["fim"] - d["commit"] for d in deploys if d["ok"]]
    pipeline = [d["fim"] - d["push"] for d in deploys if d["ok"]]

    print("## Deploys em produção\n")
    print("| Run cd | SHA | Primeiro commit | Fim em produção | Lead time | Pipeline | Resultado |")
    print("|---|---|---|---|---|---|---|")
    for d in deploys:
        if d["numero"] in revertidos:
            resultado = "revertido (rollback)"
        else:
            resultado = "ok" if d["ok"] else "falhou"
        print(f"| #{d['numero']} | `{d['sha']}` | {local(d['commit'])} | {local(d['fim'])} "
              f"| {duracao(d['fim'] - d['commit'])} | {duracao(d['fim'] - d['push'])} | {resultado} |")

    print("\n## Rollbacks\n")
    if rollbacks:
        print("| Run rollback | Início | Fim | Tempo de recuperação |")
        print("|---|---|---|---|")
        for rb in rollbacks:
            print(f"| #{rb['numero']} | {local(rb['inicio'])} | {local(rb['fim'])} "
                  f"| {duracao(rb['fim'] - rb['inicio'])} |")
    else:
        print("Nenhum rollback executado ainda.")

    print("\n## Métricas DORA\n")
    print("| Métrica | Valor |")
    print("|---|---|")
    print(f"| Frequência de deploy | {total} deploys em produção em {dias:.1f} dias "
          f"(≈ {total / dias:.1f} por dia) |")
    if lead:
        media_lead = sum(lead, timedelta()) / len(lead)
        media_pipe = sum(pipeline, timedelta()) / len(pipeline)
        print(f"| Lead time médio (primeiro commit → produção) | {duracao(media_lead)} |")
        print(f"| Tempo médio de pipeline (push na main → produção) | {duracao(media_pipe)} |")
    print(f"| Taxa de falha de mudanças | {falhas}/{total} = {100 * falhas / total:.0f}% |")
    if rollbacks:
        medio = sum((r["fim"] - r["inicio"] for r in rollbacks), timedelta()) / len(rollbacks)
        print(f"| Tempo de recuperação (rollback) | {duracao(medio)} |")
    else:
        print("| Tempo de recuperação (rollback) | sem rollback registrado |")


if __name__ == "__main__":
    main()