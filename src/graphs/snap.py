"""
Descarga y carga datasets del repositorio SNAP (Stanford Network Analysis
Project) sin necesidad de la librería oficial Snap.py.

Por qué SNAP: contiene grafos REALES (Twitter, Facebook ego nets, citaciones
arXiv, emails de Enron, web de Stanford...). 
Interesa probar los modelos no solo en grafos sintéticos sino también 
en topologías reales que exhiben los sesgos típicos de las redes sociales humanas.

Este módulo expone DOS clases:
  - `SNAPDownloader` : utilidad pura de I/O. Descarga, descomprime, cachea
                       y carga datasets como `nx.Graph` / `nx.DiGraph`.
  - `SNAPGraph`      : adapta un dataset SNAP a la interfaz `BaseGraph`
                       para que el resto del proyecto lo consuma como
                       cualquier otro grafo (delega en `SNAPDownloader`).
"""

from __future__ import annotations

# `gzip` para descomprimir los `.txt.gz` que sirve SNAP.
import gzip

# `shutil.copyfileobj` para volcar streams binarios sin cargarlos en memoria.
import shutil

# Cliente HTTP de la stdlib. Evitamos `requests` para no añadir dependencias
# y porque urllib es suficiente para una descarga simple.
import urllib.request

# `Iterable` desde `collections.abc` (PEP 585): tipado moderno.
from collections.abc import Iterable

# `dataclass` para definir `DatasetInfo` como un registro inmutable
# con campos tipados, sin escribir `__init__` a mano.
from dataclasses import dataclass

# `pathlib.Path` -> manejo de rutas multiplataforma. Mejor que strings.
from pathlib import Path

# `Any` para el dict heterogéneo que devuelve `summary()`.
from typing import Any

import networkx as nx

from src.graphs.base import BaseGraph


@dataclass(frozen=True)
class DatasetInfo:
    """
    Metadata inmutable de un dataset SNAP.

    `frozen=True` -> los campos no se pueden reasignar después de crear el
    objeto. Esto es deseable para una entrada de catálogo: actúa como
    constante. También lo hace hashable, útil si en el futuro queremos
    meterlos en un `set`.

    Campos:
      - `name`        : clave del catálogo y prefijo del fichero local.
      - `url`         : URL absoluta del .txt.gz en snap.stanford.edu.
      - `directed`    : True si el grafo original es dirigido.
      - `description` : texto humano corto, para `describe()`.
    """

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
    """
    Gestor de descarga y carga de datasets SNAP.

    Tres responsabilidades:
      1. Descargar el `.txt.gz` desde snap.stanford.edu si no está cacheado.
      2. Descomprimirlo a `.txt` para evitar pagar gzip cada lectura.
      3. Cargar el `.txt` como grafo de NetworkX (`Graph` o `DiGraph`).

    El cacheado es la clave: descargar `web-Google` (5M aristas) tarda
    bastante. Mantener todo en `cache_dir` permite reusar entre runs.

    Atributos:
      - `cache_dir` (Path): carpeta donde viven los .gz/.txt.
      - `verbose` (bool): si True, imprime el progreso.
    """

    def __init__(
        self, cache_dir: str | Path = "./data/snap", verbose: bool = True
    ) -> None:

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

    def _log(self, msg: str) -> None:
        # Centralizar el `print` evita esparcir `if verbose:` por todo el código.
        if self.verbose:
            print(msg)

    def _paths(self, name: str) -> tuple[Path, Path]:
        # Helper que devuelve las dos rutas asociadas a un dataset:
        # el .gz original (descarga) y el .txt descomprimido (lectura rápida).
        gz_path = self.cache_dir / f"raw/{name}.txt.gz"
        txt_path = self.cache_dir / f"processed/{name}.txt"
        return gz_path, txt_path

    @staticmethod
    def list_available() -> list[str]:
        # Devuelve los nombres del catálogo ordenados
        return sorted(SNAP_CATALOG.keys())

    @staticmethod
    def describe(name: str) -> str:
        # Devuelve descripción del dataset.
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
        Descarga (y opcionalmente descomprime) uno o varios datasets.

        Parámetros:
          - `names`      : un string o un iterable de strings con nombres
                           del catálogo.
          - `force`      : si True, re-descarga aunque el fichero exista.
                           Útil si el dataset ha cambiado en el origen.
          - `decompress` : si True, descomprime el .gz a .txt y devuelve la
                           ruta del .txt; si False, devuelve la del .gz.

        Devuelve un dict {nombre: ruta_final}.
        """
        # Normalización: si name es un string, se mete en una lista
        if isinstance(names, str):
            names = [names]

        result: dict[str, Path] = {}
        for name in names:
            if name not in SNAP_CATALOG:
                raise KeyError(f"Dataset '{name}' no está en el catálogo.")
            info = SNAP_CATALOG[name]
            gz_path, txt_path = self._paths(name)

            # --- Fase 1: asegurar que tenemos el .gz local ---
            if gz_path.exists() and not force:
                self._log(f"[cache] {name}: ya existe en {gz_path}")
            else:
                self._log(f"[down ] {name}: descargando desde {info.url} ...")
                self._download_file(info.url, gz_path)
                # Reportamos tamaño en MB para feedback al usuario.
                self._log(
                    f"        -> guardado en {gz_path} "
                    f"({gz_path.stat().st_size / 1e6:.2f} MB)"
                )

            # --- Fase 2: descomprimir si se pide ---
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
        """
        Carga el dataset como grafo de NetworkX.

        Asegura previamente que está descargado y descomprimido (idempotente).
        Decide `nx.Graph` vs `nx.DiGraph` según el flag del catálogo.
        """
        if name not in SNAP_CATALOG:
            raise KeyError(f"Dataset '{name}' no está en el catálogo.")

        # Descarga + descompresión bajo demanda. Si ya estaba en caché es muy rápido.
        paths = self.download(name, decompress=True)
        txt_path = paths[name]
        info = SNAP_CATALOG[name]

        # Truco común: pasar la CLASE (no una instancia) en `create_using`.
        # NetworkX la instancia internamente.
        create_using = nx.DiGraph if info.directed else nx.Graph

        # Los ficheros SNAP son edge-lists: dos enteros por línea, comentarios con `#`.
        # `nodetype=int` convierte los IDs a int (vienen como strings por defecto).
        return nx.read_edgelist(
            txt_path, comments="#", create_using=create_using(), nodetype=int
        )

    def summary(self, name: str) -> dict[str, Any]:
        """
        Devuelve un resumen rápido del dataset SIN cargarlo en memoria.

        Útil para datasets enormes (millones de aristas) en los que cargar
        el grafo entero solo para contar nodos sería un desperdicio.
        Itera línea a línea y mantiene un `set` de nodos vistos.
        """
        paths = self.download(name, decompress=True)
        txt_path = paths[name]
        edges = 0
        nodes: set[int] = set()
        with open(txt_path) as f:
            for line in f:
                # Saltamos comentarios y líneas vacías típicos de SNAP.
                if line.startswith("#") or not line.strip():
                    continue
                # `split()[:2]` por si la línea trae más de 2 columnas (peso, etc.).
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
        # Helper estático y privado (`_`). Hace una sola cosa: bajar bytes.
        # Falseamos User-Agent porque SNAP rechaza el de urllib por defecto
        # (lo confunde con un bot abusivo). Mozilla/5.0 es el "user-agent canónico".
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (SNAPDownloader)"}
        )
        # Doble `with`: cierra automáticamente la conexión HTTP y el fichero
        # local aunque haya excepción a mitad de descarga.
        # `copyfileobj` copia en chunks: NUNCA carga el fichero entero en RAM.
        with urllib.request.urlopen(req) as resp, open(dest, "wb") as out:
            shutil.copyfileobj(resp, out)

    @staticmethod
    def _gunzip(src: Path, dest: Path) -> None:
        # Mismo patrón: streaming, sin cargar todo en memoria.
        # `gzip.open(..., "rb")` te da un file-like binario que descomprime al vuelo.
        with gzip.open(src, "rb") as f_in, open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


class SNAPGraph(BaseGraph):
    """
    Adaptador de un dataset SNAP a la interfaz `BaseGraph`.

    Composición sobre herencia: `SNAPGraph` NO hereda de `SNAPDownloader`,
    sino que tiene uno como atributo (`self.downloader`). Así separamos:
      - `SNAPDownloader` = lógica de I/O (descarga, caché, parsing).
      - `SNAPGraph`      = adaptador a la interfaz del proyecto.

    Atributos:
      - `dataset_name` (str): clave del catálogo (p.ej. "ca-GrQc").
      - `cache_dir`    : carpeta de caché. Por defecto vive bajo `src/data/snap`.
      - `seed`         : heredado de `BaseGraph`. SNAP no usa seeds (los
                         grafos son fijos), pero respetamos la firma común.
      - `downloader`   : instancia de `SNAPDownloader` que hace el trabajo real.
    """

    def __init__(
        self,
        dataset_name: str,
        cache_dir: str | Path = "./data/snap",
        seed: int | None = None,
    ) -> None:
        
        super().__init__(seed=seed)
        self.dataset_name = dataset_name
        self.cache_dir = cache_dir
        # Composición: delegamos toda la lógica de descarga al downloader.
        self.downloader = SNAPDownloader(cache_dir=cache_dir, verbose=True)

    def build(self) -> nx.Graph:
        # Cumplimos con el contrato de `BaseGraph`: devolver un `nx.Graph`.
        # Internamente delega en el downloader. La caché lazy de `BaseGraph`
        # garantiza que solo se descargue/parsee una vez aunque se acceda
        # a `.graph` muchas veces.
        return self.downloader.load_as_networkx(self.dataset_name)
