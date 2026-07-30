#!/usr/bin/env python3
"""Os seis estados têm realidades distintas? Teste formal.

Há três especificações possíveis, aninhadas uma na outra:

  A. Comum      — um intercepto e uma inclinação para todos os municípios
  B. Efeitos fixos — um intercepto por estado, inclinações comuns
                     (é "estado como variável categórica")
  C. Interações — um intercepto E uma inclinação por estado
                  (equivale a seis modelos separados, estimados em conjunto)

Rodar seis modelos separados é o mesmo que assumir C sem testá-la. A pergunta
"cada estado tem uma realidade distinta" é exatamente a comparação B contra C:
se as inclinações não diferem além do esperado por acaso, C só acrescenta
ruído, e B é a especificação correta.

O teste é um F para modelos aninhados, com a mesma padronização em todos os
estados — sem isso os coeficientes não são comparáveis entre si.

Saída: site/dados/heterogeneidade.json e relatório em texto.
"""
import json, os, importlib.util
import numpy as np

AQUI = os.path.dirname(__file__)
SITE = os.path.join(AQUI, "..", "site", "dados")

spec = importlib.util.spec_from_file_location(
    "base", os.path.join(AQUI, "06_modelagem.py"))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

UFS, PRE, ROTULOS = base.UFS, base.PRE, base.ROTULOS
NOMES_UF = base.NOMES_UF


def ssr_ponderado(X, y, w):
    A = np.c_[np.ones(len(X)), X]
    sw = np.sqrt(w)
    b, *_ = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)
    res = y - A @ b
    return float(w @ res ** 2), b, A.shape[1]


def teste_f(ssr_r, k_r, ssr_u, k_u, n):
    """F de modelos aninhados. Devolve (F, gl1, gl2, p)."""
    from scipy import stats
    gl1, gl2 = k_u - k_r, n - k_u
    F = ((ssr_r - ssr_u) / gl1) / (ssr_u / gl2)
    return F, gl1, gl2, float(stats.f.sf(F, gl1, gl2))


def main():
    linhas = base.carrega()
    n = len(linhas)
    print(f"Municípios: {n}   Desfecho: logito de brancos + nulos "
          f"({base.CARGO}, {base.ANO})\n")

    # Padronização ÚNICA, sobre o conjunto agrupado. É o que torna a
    # inclinação de São Paulo comparável à do Pará.
    X = np.array([[l[v] for v in PRE] for l in linhas], float)
    y = np.array([l["y"] for l in linhas])
    w = np.array([l["w"] for l in linhas])
    Z = (X - X.mean(0)) / X.std(0)
    uf = np.array([l["uf"] for l in linhas])
    D = np.column_stack([(uf == u).astype(float) for u in UFS[1:]])

    # --- as três especificações ---
    ssr_a, _, k_a = ssr_ponderado(Z, y, w)
    ssr_b, _, k_b = ssr_ponderado(np.c_[Z, D], y, w)
    inter = np.column_stack([Z[:, [i]] * D[:, [j]]
                             for i in range(len(PRE)) for j in range(D.shape[1])])
    ssr_c, _, k_c = ssr_ponderado(np.c_[Z, D, inter], y, w)

    print("=" * 72)
    print("ESPECIFICAÇÕES ANINHADAS")
    print("=" * 72)
    for nome, ssr, k in [("A. inclinações e intercepto comuns", ssr_a, k_a),
                         ("B. intercepto por estado (categórica)", ssr_b, k_b),
                         ("C. intercepto e inclinação por estado", ssr_c, k_c)]:
        print(f"  {nome:42} parâmetros={k:4}  SQR={ssr:12.1f}")

    print("\n" + "=" * 72)
    print("A REALIDADE DE CADA ESTADO É DISTINTA?")
    print("=" * 72)
    F, g1, g2, p = teste_f(ssr_a, k_a, ssr_b, k_b, n)
    print(f"\n  B contra A — os NÍVEIS diferem entre estados?")
    print(f"    F({g1}, {g2}) = {F:.2f}   p = {p:.3e}")
    print(f"    {'sim' if p<.05 else 'não'}: "
          f"{'cada estado tem seu próprio patamar de não-voto' if p<.05 else 'sem diferença de patamar'}")

    Fc, g1c, g2c, pc = teste_f(ssr_b, k_b, ssr_c, k_c, n)
    print(f"\n  C contra B — as INCLINAÇÕES diferem entre estados?")
    print(f"    F({g1c}, {g2c}) = {Fc:.2f}   p = {pc:.3e}")
    print(f"    {'sim' if pc<.05 else 'não'}: "
          f"{'o mesmo indicador age de forma diferente em cada estado' if pc<.05 else 'o efeito dos indicadores é o mesmo em todos os estados'}")

    res = {"n": n,
           "ssr": {"A": ssr_a, "B": ssr_b, "C": ssr_c},
           "k": {"A": k_a, "B": k_b, "C": k_c},
           "niveis": {"F": round(F, 3), "gl1": g1, "gl2": g2, "p": p},
           "inclinacoes": {"F": round(Fc, 3), "gl1": g1c, "gl2": g2c, "p": pc},
           "por_variavel": []}

    # --- qual inclinação, especificamente, varia entre estados? ---
    print("\n" + "=" * 72)
    print("QUAIS INDICADORES VARIAM DE ESTADO PARA ESTADO")
    print("=" * 72)
    print("  Cada linha retira do modelo C as interações de UMA variável e")
    print("  testa se a piora é maior que o acaso.\n")
    print(f"  {'variável':<30}{'F':>8}{'p':>12}   veredito")
    ordem = []
    for i, v in enumerate(PRE):
        manter = [c for c in range(inter.shape[1]) if c // D.shape[1] != i]
        ssr_r, _, k_r = ssr_ponderado(np.c_[Z, D, inter[:, manter]], y, w)
        Fi, _, _, pi = teste_f(ssr_r, k_r, ssr_c, k_c, n)
        ordem.append((pi, Fi, v))
    for pi, Fi, v in sorted(ordem):
        vered = "varia entre estados" if pi < .05 else "estável"
        print(f"  {ROTULOS[v]:<30}{Fi:>8.2f}{pi:>12.4f}   {vered}")
        res["por_variavel"].append(
            {"var": ROTULOS[v], "F": round(Fi, 2), "p": round(pi, 5),
             "varia": bool(pi < .05)})

    # --- inclinações por estado, na mesma escala ---
    print("\n" + "=" * 72)
    print("INCLINAÇÕES POR ESTADO, NA MESMA ESCALA")
    print("=" * 72)
    res["slopes"] = {}
    cab = f"  {'variável':<30}" + "".join(f"{u:>9}" for u in UFS)
    print(cab)
    for i, v in enumerate(PRE):
        linha = f"  {ROTULOS[v]:<30}"
        res["slopes"][ROTULOS[v]] = {}
        for u in UFS:
            m = uf == u
            _, b, _ = ssr_ponderado(Z[m], y[m], w[m])
            linha += f"{b[1+i]:>9.3f}"
            res["slopes"][ROTULOS[v]][u] = round(float(b[1 + i]), 4)
        print(linha)

    print("\n" + "=" * 72)
    print("RESSALVA")
    print("=" * 72)
    print("  O I de Moran mostrou resíduos agrupados no espaço. O teste F supõe")
    print("  observações independentes, então o p acima é otimista — a")
    print("  evidência de heterogeneidade é mais fraca do que o número sugere.")

    with open(os.path.join(SITE, "heterogeneidade.json"), "w") as f:
        json.dump(res, f, ensure_ascii=False, separators=(",", ":"))
    print("\nGravado: site/dados/heterogeneidade.json")


if __name__ == "__main__":
    main()
