#!/usr/bin/env python3
"""
analitza_logs.py — Analitza un registre d'accés d'Apache/Nginx (format combinat)
i genera un informe: peticions totals, codis d'estat, IP més actives, rutes
més demanades i percentatge d'errors.

Només fa servir la biblioteca estàndard de Python (sense dependències).

Exemples:
    python analitza_logs.py mostres/access.log
    python analitza_logs.py mostres/access.log --top 3
    python analitza_logs.py mostres/access.log --json informe.json
    python analitza_logs.py mostres/access.log --max-errors 20
    cat access.log | python analitza_logs.py -

Codis d'eixida:
    0  tot correcte
    1  el percentatge d'errors (4xx + 5xx) supera --max-errors
    2  error d'ús (fitxer inexistent, fitxer sense cap línia vàlida...)
"""

import argparse
import json
import re
import sys
from collections import Counter

# 192.168.1.10 - - [18/Oct/2026:10:15:32 +0200] "GET /index.html HTTP/1.1" 200 5120 "-" "Mozilla/5.0"
PATRO = re.compile(
    r'^(?P<ip>\S+) \S+ \S+ \[(?P<data>[^\]]+)\] '
    r'"(?P<metode>[A-Z]+) (?P<ruta>\S+) [^"]*" '
    r'(?P<estat>\d{3}) (?P<mida>\d+|-)'
)


def analitza_linia(linia):
    """Converteix una línia del registre en un diccionari, o None si no és vàlida."""
    coincidencia = PATRO.match(linia.strip())
    if not coincidencia:
        return None
    dades = coincidencia.groupdict()
    dades["estat"] = int(dades["estat"])
    dades["mida"] = 0 if dades["mida"] == "-" else int(dades["mida"])
    return dades


def analitza(linies):
    """Recorre totes les línies i en torna un resum."""
    estats = Counter()
    ips = Counter()
    rutes = Counter()
    total = invalides = errors = bytes_totals = 0

    for linia in linies:
        if not linia.strip():
            continue
        peticio = analitza_linia(linia)
        if peticio is None:
            invalides += 1
            continue
        total += 1
        estats[peticio["estat"]] += 1
        ips[peticio["ip"]] += 1
        rutes[peticio["ruta"]] += 1
        bytes_totals += peticio["mida"]
        if peticio["estat"] >= 400:
            errors += 1

    percentatge_errors = round(100 * errors / total, 1) if total else 0.0
    return {
        "total": total,
        "invalides": invalides,
        "errors": errors,
        "percentatge_errors": percentatge_errors,
        "bytes": bytes_totals,
        "estats": dict(sorted(estats.items())),
        "ips": ips,
        "rutes": rutes,
    }


def format_informe(resum, top=5):
    """Construeix l'informe en text per a mostrar-lo per pantalla."""
    linies = [
        "=== Informe del registre d'accés ===",
        f"Peticions vàlides : {resum['total']}",
        f"Línies invàlides  : {resum['invalides']}",
        f"Bytes servits     : {resum['bytes']}",
        f"Errors (4xx/5xx)  : {resum['errors']} ({resum['percentatge_errors']} %)",
        "",
        "Codis d'estat:",
    ]
    for estat, quantitat in resum["estats"].items():
        linies.append(f"  {estat}: {quantitat}")
    linies.append("")
    linies.append(f"Top {top} IP:")
    for ip, quantitat in resum["ips"].most_common(top):
        linies.append(f"  {ip:<16} {quantitat}")
    linies.append("")
    linies.append(f"Top {top} rutes:")
    for ruta, quantitat in resum["rutes"].most_common(top):
        linies.append(f"  {ruta:<24} {quantitat}")
    return "\n".join(linies)


def a_json(resum, top=5):
    """Versió serialitzable del resum (per a guardar-la com a artifact)."""
    return {
        "total": resum["total"],
        "invalides": resum["invalides"],
        "errors": resum["errors"],
        "percentatge_errors": resum["percentatge_errors"],
        "bytes": resum["bytes"],
        "estats": {str(k): v for k, v in resum["estats"].items()},
        "top_ips": resum["ips"].most_common(top),
        "top_rutes": resum["rutes"].most_common(top),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Analitza un registre d'accés d'Apache/Nginx (format combinat)."
    )
    parser.add_argument("fitxer", help="camí del registre, o '-' per a llegir de l'entrada estàndard")
    parser.add_argument("--top", type=int, default=5, help="quantes IP i rutes mostrar (per defecte 5)")
    parser.add_argument("--json", metavar="EIXIDA", help="guarda també el resum en un fitxer JSON")
    parser.add_argument(
        "--max-errors", type=float, metavar="PCT",
        help="acaba amb codi 1 si el percentatge d'errors supera PCT",
    )
    args = parser.parse_args(argv)

    try:
        if args.fitxer == "-":
            linies = sys.stdin.readlines()
        else:
            with open(args.fitxer, encoding="utf-8") as f:
                linies = f.readlines()
    except OSError as e:
        print(f"Error: no es pot llegir '{args.fitxer}': {e.strerror}", file=sys.stderr)
        return 2

    resum = analitza(linies)
    if resum["total"] == 0:
        print("Error: el fitxer no conté cap línia vàlida.", file=sys.stderr)
        return 2

    print(format_informe(resum, args.top))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(a_json(resum, args.top), f, ensure_ascii=False, indent=2)
        print(f"\nResum JSON guardat a {args.json}")

    if args.max_errors is not None and resum["percentatge_errors"] > args.max_errors:
        print(
            f"\nALERTA: {resum['percentatge_errors']} % d'errors supera el màxim de {args.max_errors} %",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
