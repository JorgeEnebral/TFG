"""
snap_downloader.py
------------------
Descarga datasets del repositorio SNAP (Stanford Network Analysis Project)
sin necesidad de instalar la librería Snap.py.

Uso básico:
    dl = SNAPDownloader(cache_dir="./snap_data")
    paths = dl.download(["soc-Epinions1", "ca-GrQc"])
    G = dl.load_as_networkx("soc-Epinions1")  # requiere networkx
"""

from __future__ import annotations

import gzip
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


# ---------------------------------------------------------------------------
# Catálogo de datasets SNAP más usados.
# Cada entrada contiene: URL del archivo .gz, si el grafo es dirigido,
# y una breve descripción.
# Puedes añadir más desde https://snap.stanford.edu/data/
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DatasetInfo:
    name: str
    url: str
    directed: bool
    description: str


SNAP_CATALOG: dict[str, DatasetInfo] = {
    # --- Redes sociales ---
    "soc-Epinions1": DatasetInfo(
        name="soc-Epinions1",
        url="https://snap.stanford.edu/data/soc-Epinions1.txt.gz",
        directed=True,
        description="Red de confianza de Epinions.com (75k nodos, 508k aristas)",
    ),
    "soc-Slashdot0811": DatasetInfo(
        name="soc-Slashdot0811",
        url="https://snap.stanford.edu/data/soc-Slashdot0811.txt.gz",
        directed=True,
        description="Red social de Slashdot (Nov 2008)",
    ),
    "soc-LiveJournal1": DatasetInfo(
        name="soc-LiveJournal1",
        url="https://snap.stanford.edu/data/soc-LiveJournal1.txt.gz",
        directed=True,
        description="Red de amistades de LiveJournal (4.8M nodos, 69M aristas)",
    ),
    "ego-Facebook": DatasetInfo(
        name="ego-Facebook",
        url="https://snap.stanford.edu/data/facebook_combined.txt.gz",
        directed=False,
        description="Círculos sociales de Facebook (4k nodos, 88k aristas)",
    ),
    "ego-Twitter": DatasetInfo(
        name="ego-Twitter",
        url="https://snap.stanford.edu/data/twitter_combined.txt.gz",
        directed=True,
        description="Círculos sociales de Twitter (81k nodos, 1.7M aristas)",
    ),
    # --- Redes de colaboración / citación ---
    "ca-GrQc": DatasetInfo(
        name="ca-GrQc",
        url="https://snap.stanford.edu/data/ca-GrQc.txt.gz",
        directed=False,
        description="Colaboración arXiv General Relativity (5k nodos)",
    ),
    "ca-HepTh": DatasetInfo(
        name="ca-HepTh",
        url="https://snap.stanford.edu/data/ca-HepTh.txt.gz",
        directed=False,
        description="Colaboración arXiv High Energy Physics Theory (9k nodos)",
    ),
    "cit-HepPh": DatasetInfo(
        name="cit-HepPh",
        url="https://snap.stanford.edu/data/cit-HepPh.txt.gz",
        directed=True,
        description="Red de citaciones arXiv HEP-PH (34k nodos, 421k aristas)",
    ),
    # --- Redes de comunicación ---
    "email-Enron": DatasetInfo(
        name="email-Enron",
        url="https://snap.stanford.edu/data/email-Enron.txt.gz",
        directed=False,
        description="Red de emails de Enron (36k nodos, 183k aristas)",
    ),
    "email-EuAll": DatasetInfo(
        name="email-EuAll",
        url="https://snap.stanford.edu/data/email-EuAll.txt.gz",
        directed=True,
        description="Red de emails de una institución europea de investigación",
    ),
    # --- Redes web ---
    "web-Stanford": DatasetInfo(
        name="web-Stanford",
        url="https://snap.stanford.edu/data/web-Stanford.txt.gz",
        directed=True,
        description="Red web de stanford.edu (281k nodos, 2.3M aristas)",
    ),
    "web-Google": DatasetInfo(
        name="web-Google",
        url="https://snap.stanford.edu/data/web-Google.txt.gz",
        directed=True,
        description="Red web publicada por Google (875k nodos, 5.1M aristas)",
    ),
    # --- P2P ---
    "p2p-Gnutella08": DatasetInfo(
        name="p2p-Gnutella08",
        url="https://snap.stanford.edu/data/p2p-Gnutella08.txt.gz",
        directed=True,
        description="Red P2P Gnutella (Ago 2002)",
    ),
    # --- Firmas / Wiki ---
    "wiki-Vote": DatasetInfo(
        name="wiki-Vote",
        url="https://snap.stanford.edu/data/wiki-Vote.txt.gz",
        directed=True,
        description="Votaciones de administradores de Wikipedia (7k nodos)",
    ),
}


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------
class SNAPDownloader:
    """Gestor de descarga y carga de datasets del repositorio SNAP."""

    def __init__(self, cache_dir: str | Path = "./snap_data", verbose: bool = True):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

    # ---------- utilidades internas ----------
    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _paths(self, name: str) -> tuple[Path, Path]:
        """Devuelve (ruta .gz, ruta .txt descomprimido) para un dataset."""
        gz_path = self.cache_dir / f"{name}.txt.gz"
        txt_path = self.cache_dir / f"{name}.txt"
        return gz_path, txt_path

    # ---------- API pública ----------
    @staticmethod
    def list_available() -> list[str]:
        """Lista los nombres de datasets disponibles en el catálogo."""
        return sorted(SNAP_CATALOG.keys())

    @staticmethod
    def describe(name: str) -> str:
        """Devuelve la descripción de un dataset."""
        if name not in SNAP_CATALOG:
            raise KeyError(f"Dataset '{name}' no está en el catálogo.")
        info = SNAP_CATALOG[name]
        kind = "dirigido" if info.directed else "no dirigido"
        return f"{info.name} [{kind}]: {info.description}\n  URL: {info.url}"

    def download(
        self,
        names: str | Iterable[str],
        force: bool = False,
        decompress: bool = True,
    ) -> dict[str, Path]:
        """
        Descarga uno o varios datasets.

        Parameters
        ----------
        names : str o iterable de str
            Nombre(s) del dataset en el catálogo.
        force : bool
            Si True, re-descarga aunque ya exista en caché.
        decompress : bool
            Si True, descomprime el .gz a .txt.

        Returns
        -------
        dict[str, Path]
            Diccionario {nombre: ruta_final} con la ruta al archivo usable
            (el .txt si decompress=True, si no el .gz).
        """
        if isinstance(names, str):
            names = [names]

        result: dict[str, Path] = {}
        for name in names:
            if name not in SNAP_CATALOG:
                raise KeyError(
                    f"Dataset '{name}' no está en el catálogo. "
                    f"Usa SNAPDownloader.list_available() para ver las opciones."
                )
            info = SNAP_CATALOG[name]
            gz_path, txt_path = self._paths(name)

            # Descarga del .gz
            if gz_path.exists() and not force:
                self._log(f"[cache] {name}: ya existe en {gz_path}")
            else:
                self._log(f"[down ] {name}: descargando desde {info.url} ...")
                self._download_file(info.url, gz_path)
                self._log(f"        -> guardado en {gz_path} "
                          f"({gz_path.stat().st_size / 1e6:.2f} MB)")

            # Descompresión
            if decompress:
                if txt_path.exists() and not force:
                    self._log(f"[cache] {name}: ya descomprimido en {txt_path}")
                else:
                    self._log(f"[unzip] {name}: descomprimiendo ...")
                    self._gunzip(gz_path, txt_path)
                    self._log(f"        -> {txt_path} "
                              f"({txt_path.stat().st_size / 1e6:.2f} MB)")
                result[name] = txt_path
            else:
                result[name] = gz_path

        return result

    def load_as_networkx(self, name: str):
        """
        Carga el dataset como grafo de NetworkX.
        Requiere la librería networkx instalada.
        """
        try:
            import networkx as nx
        except ImportError as e:
            raise ImportError(
                "networkx no está instalado. Instálalo con: pip install networkx"
            ) from e

        if name not in SNAP_CATALOG:
            raise KeyError(f"Dataset '{name}' no está en el catálogo.")

        # Aseguramos que esté descargado y descomprimido
        paths = self.download(name, decompress=True)
        txt_path = paths[name]

        info = SNAP_CATALOG[name]
        create_using = nx.DiGraph if info.directed else nx.Graph

        self._log(f"[load ] {name}: cargando grafo {'dirigido' if info.directed else 'no dirigido'} ...")
        # Los ficheros SNAP empiezan con líneas de comentario '#'
        G = nx.read_edgelist(
            txt_path,
            comments="#",
            create_using=create_using(),
            nodetype=int,
        )
        self._log(f"        -> {G.number_of_nodes()} nodos, {G.number_of_edges()} aristas")
        return G

    def summary(self, name: str) -> dict:
        """Devuelve un resumen rápido del grafo (sin cargar todo en memoria)."""
        paths = self.download(name, decompress=True)
        txt_path = paths[name]
        edges = 0
        nodes: set[int] = set()
        with open(txt_path) as f:
            for line in f:
                if line.startswith("#") or not line.strip():
                    continue
                u, v = line.split()[:2]
                nodes.add(int(u))
                nodes.add(int(v))
                edges += 1
        info = SNAP_CATALOG[name]
        return {
            "name": name,
            "directed": info.directed,
            "nodes": len(nodes),
            "edges": edges,
            "file": str(txt_path),
        }

    # ---------- helpers de bajo nivel ----------
    @staticmethod
    def _download_file(url: str, dest: Path) -> None:
        """Descarga con urllib. SNAP rechaza el UA por defecto, por eso lo falseamos."""
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (SNAPDownloader)"},
        )
        with urllib.request.urlopen(req) as resp, open(dest, "wb") as out:
            shutil.copyfileobj(resp, out)

    @staticmethod
    def _gunzip(src: Path, dest: Path) -> None:
        with gzip.open(src, "rb") as f_in, open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


# ---------------------------------------------------------------------------
# Demo ejecutable
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    dl = SNAPDownloader(cache_dir="./snap_data")

    print("=== Datasets disponibles en el catálogo ===")
    for n in dl.list_available():
        print(" -", n)

    # Ejemplo: descargamos dos datasets pequeños
    targets = ["wiki-Vote", "ca-GrQc"]
    print(f"\n=== Descargando {targets} ===")
    paths = dl.download(targets)
    for name, p in paths.items():
        print(f" {name} -> {p}")

    # Resumen sin networkx
    print("\n=== Resumen ===")
    for name in targets:
        print(dl.summary(name))
