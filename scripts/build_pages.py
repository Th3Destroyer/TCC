#!/usr/bin/env python3
"""Atualiza os arquivos estáticos do GitHub Pages sem instalar Django."""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from desk.help_content import INITIAL_ARTICLES


def main():
    assets = ROOT / "docs" / "assets"
    assets.mkdir(exist_ok=True)
    for source, destination in [
        (ROOT / "static/desk/app.css", assets / "base.css"),
        (ROOT / "static/desk/help.css", assets / "help.css"),
        (ROOT / "templates/desk/_icons.html", assets / "icons.svg"),
    ]:
        shutil.copyfile(source, destination)
    categories = ["Hardware", "Software", "Conectividade", "Impressoras", "Telefonia", "Criação de usuários"]
    data = {
        "categories": categories,
        "departments": ["Administração", "Educação", "Saúde", "Finanças", "Obras", "Assistência Social"],
        "articles": [dict(article, id=index, published=True) for index, article in enumerate(INITIAL_ARTICLES, start=1)],
    }
    (assets / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("GitHub Pages: estilos, ícones e dez orientações atualizados em docs/assets.")


if __name__ == "__main__":
    main()
