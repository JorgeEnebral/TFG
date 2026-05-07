"""
Descarga y carga datasets del repositorio SNAP (Stanford Network Analysis
Project) sin necesidad de la librería Snap.py.
"""

from __future__ import annotations

import gzip
import shutil
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx

from src.graphs.base import BaseGraph


@dataclass(frozen=True)
class DatasetInfo:
    name: str
    url: str
    directed: bool
    description: str


SNAP_CATALOG: dict[str, DatasetInfo] = {
    "soc-Epinions1": DatasetInfo(
        "soc-Epinions1",
        "https://snap.stanford.edu/data/soc-Epinions1.txt.gz",
        True,
        "Red de confianza de Epinions.com (75k nodos, 508k aristas)",
    ),
    "soc-Slashdot0811": DatasetInfo(
        "soc-Slashdot0811",
        "https://snap.stanford.edu/data/soc-Slashdot0811.txt.gz",
        True,
        "Red social de Slashdot (Nov 2008)",
    ),
    "soc-LiveJournal1": DatasetInfo(
        "soc-LiveJournal1",
        "https://snap.stanford.edu/data/soc-LiveJournal1.txt.gz",
        True,
        "Red de amistades de LiveJournal (4.8M nodos, 69M aristas)",
    ),
    "ego-Facebook": DatasetInfo(
        "ego-Facebook",
        "https://snap.stanford.edu/data/facebook_combined.txt.gz",
        False,
        "Círculos sociales de Facebook (4k nodos, 88k aristas)",
    ),
    "ego-Twitter": DatasetInfo(
        "ego-Twitter",
        "https://snap.stanford.edu/data/twitter_combined.txt.gz",
        True,
        "Círculos sociales de Twitter (81k nodos, 1.7M aristas)",
    ),
    "ca-GrQc": DatasetInfo(
        "ca-GrQc",
        "https://snap.stanford.edu/data/ca-GrQc.txt.gz",
        False,
        "Colaboración arXiv General Relativity (5k nodos)",
    ),
    "ca-HepTh": DatasetInfo(
        "ca-HepTh",
        "https://snap.stanford.edu/data/ca-HepTh.txt.gz",
        False,
        "Colaboración arXiv High Energy Physics Theory (9k nodos)",
    ),
    "cit-HepPh": DatasetInfo(
        "cit-HepPh",
        "https://snap.stanford.edu/data/cit-HepPh.txt.gz",
        True,
        "Red de citaciones arXiv HEP-PH (34k nodos, 421k aristas)",
    ),
    "email-Enron": DatasetInfo(
        "email-Enron",
        "https://snap.stanford.edu/data/email-Enron.txt.gz",
        False,
        "Red de emails de Enron (36k nodos, 183k aristas)",
    ),
    "email-EuAll": DatasetInfo(
        "email-EuAll",
        "https://snap.stanford.edu/data/email-EuAll.txt.gz",
        True,
        "Red de emails de una institución europea de investigación",
    ),
    "web-Stanford": DatasetInfo(
        "web-Stanford",
        "https://snap.stanford.edu/data/web-Stanford.txt.gz",
        True,
        "Red web de stanford.edu (281k nodos, 2.3M aristas)",
    ),
    "web-Google": DatasetInfo(
        "web-Google",
        "https://snap.stanford.edu/data/web-Google.txt.gz",
        True,
        "Red web publicada por Google (875k nodos, 5.1M aristas)",
    ),
    "p2p-Gnutella08": DatasetInfo(
        "p2p-Gnutella08",
        "https://snap.stanford.edu/data/p2p-Gnutella08.txt.gz",
        True,
        "Red P2P Gnutella (Ago 2002)",
    ),
    "wiki-Vote": DatasetInfo(
        "wiki-Vote",
        "https://snap.stanford.edu/data/wiki-Vote.txt.gz",
        True,
        "Votaciones de administradores de Wikipedia (7k nodos)",
    ),
}


class SNAPDownloader:
    """Gestor de descarga y carga de datasets SNAP."""

    def __init__(
        self, cache_dir: str | Path = "./src/data/snap", verbose: bool = True
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _paths(self, name: str) -> tuple[Path, Path]:
        gz_path = self.cache_dir / f"{name}.txt.gz"
        txt_path = self.cache_dir / f"{name}.txt"
        return gz_path, txt_path

    @staticmethod
    def list_available() -> list[str]:
        return sorted(SNAP_CATALOG.keys())

    @staticmethod
    def describe(name: str) -> str:
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
        if isinstance(names, str):
            names = [names]

        result: dict[str, Path] = {}
        for name in names:
            if name not in SNAP_CATALOG:
                raise KeyError(f"Dataset '{name}' no está en el catálogo.")
            info = SNAP_CATALOG[name]
            gz_path, txt_path = self._paths(name)

            if gz_path.exists() and not force:
                self._log(f"[cache] {name}: ya existe en {gz_path}")
            else:
                self._log(f"[down ] {name}: descargando desde {info.url} ...")
                self._download_file(info.url, gz_path)
                self._log(
                    f"        -> guardado en {gz_path} "
                    f"({gz_path.stat().st_size / 1e6:.2f} MB)"
                )

            if decompress:
                if txt_path.exists() and not force:
                    self._log(f"[cache] {name}: ya descomprimido en {txt_path}")
                else:
                    self._log(f"[unzip] {name}: descomprimiendo ...")
                    self._gunzip(gz_path, txt_path)
                result[name] = txt_path
            else:
                result[name] = gz_path

        return result

    def load_as_networkx(self, name: str) -> nx.Graph:
        if name not in SNAP_CATALOG:
            raise KeyError(f"Dataset '{name}' no está en el catálogo.")
        paths = self.download(name, decompress=True)
        txt_path = paths[name]
        info = SNAP_CATALOG[name]
        create_using = nx.DiGraph if info.directed else nx.Graph
        return nx.read_edgelist(
            txt_path, comments="#", create_using=create_using(), nodetype=int
        )

    def summary(self, name: str) -> dict[str, Any]:
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

    @staticmethod
    def _download_file(url: str, dest: Path) -> None:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (SNAPDownloader)"}
        )
        with urllib.request.urlopen(req) as resp, open(dest, "wb") as out:
            shutil.copyfileobj(resp, out)

    @staticmethod
    def _gunzip(src: Path, dest: Path) -> None:
        with gzip.open(src, "rb") as f_in, open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


class SNAPGraph(BaseGraph):
    """Adaptador de un dataset SNAP a la interfaz `BaseGraph`."""

    def __init__(
        self,
        dataset_name: str,
        cache_dir: str | Path = "./src/data/snap",
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.dataset_name = dataset_name
        self.cache_dir = cache_dir
        self.downloader = SNAPDownloader(cache_dir=cache_dir, verbose=True)

    def build(self) -> nx.Graph:
        return self.downloader.load_as_networkx(self.dataset_name)
