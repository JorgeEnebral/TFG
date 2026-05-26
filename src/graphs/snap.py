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

# Cliente HTTP de la stdlib. Evita añadir la dependencia `requests`
# porque urllib es suficiente para una descarga simple.
import urllib.request

# `Iterable` desde `collections.abc` (PEP 585): tipado moderno.
from collections.abc import Iterable

# `dataclass` para definir `DatasetInfo` como un registro inmutable
# con campos tipados, sin escribir `__init__` a mano.
from dataclasses import dataclass

# `pathlib.Path` -> manejo de rutas multiplataforma. Mejor que strings.
from pathlib import Path


import networkx as nx
import random

from src.graphs.base import BaseGraph
from src.messages import Layer


@dataclass(frozen=True)
class DatasetInfo:
    """Metadata inmutable de un dataset SNAP.

    `frozen=True` -> los campos no se pueden reasignar después de crear el
    objeto. Esto es deseable para una entrada de catálogo: actúa como
    constante. También lo hace hashable, útil si en el futuro queremos
    meterlos en un `set`.

    Attributes:
        name: Clave del catálogo y prefijo del fichero local.
        url: URL absoluta del .txt.gz en snap.stanford.edu.
        directed: True si el grafo original es dirigido.
        description: Texto humano corto, para `describe()`.
    """

    name: str
    url: str
    directed: bool
    description: str


SNAP_CATALOG: dict[str, DatasetInfo] = {
    # ------------------------------------------------------------------ #
    # NO DIRIGIDOS                                                         #
    # ------------------------------------------------------------------ #

    # Red social de Facebook anonimizada: ego-networks de 10 usuarios reales.
    # Nodos = personas, aristas = amistad mutua. Datos: círculos sociales
    # (listas de amigos), atributos de perfil anonimizados, ego-features.
    # Útil para detección de comunidades y embedding de grafos sociales.
    "ego-Facebook": DatasetInfo(
        "ego-Facebook",
        "https://snap.stanford.edu/data/facebook_combined.txt.gz",
        False,
        "Círculos sociales de Facebook (4k nodos, 88k aristas)",
    ),

    # Red social de la plataforma de check-in Gowalla (feb. 2009 – oct. 2010).
    # Nodos = usuarios, aristas = amistad declarada en la app.
    # Datos extra: 6,4 M check-ins con marca de tiempo, latitud/longitud
    # e identificador de lugar. Sirve para análisis de movilidad urbana
    # y recomendación de puntos de interés (POI recommendation).
    "loc-Gowalla": DatasetInfo(
        "loc-Gowalla",
        "https://snap.stanford.edu/data/loc-gowalla_edges.txt.gz",
        False,
        "Red social con check-ins de Gowalla (196k nodos, 950k aristas)",
    ),

    # Red social de la plataforma de check-in Brightkite (abr. 2008 – oct. 2010).
    # Nodos = usuarios, aristas = amistad mutua (el grafo original era
    # dirigido; SNAP publica la versión no dirigida con aristas recíprocas).
    # Datos extra: 4,5 M check-ins con tiempo, coordenadas e ID de lugar.
    # Similar a Gowalla, ideal para estudios de difusión y movilidad.
    "loc-Brightkite": DatasetInfo(
        "loc-Brightkite",
        "https://snap.stanford.edu/data/loc-brightkite_edges.txt.gz",
        False,
        "Red social con check-ins de Brightkite (58k nodos, 214k aristas)",
    ),

    # ------------------------------------------------------------------ #
    # DIRIGIDOS                                                            #
    # ------------------------------------------------------------------ #

    # Red de confianza del sitio de reseñas de consumidor Epinions.com.
    # Nodos = usuarios, aristas dirigidas = "A confía en B".
    # Es la versión básica (solo trust). Estudia propagación de confianza
    # y ranking de reseñas. Benchmark clásico para PageRank y HITS.
    "soc-Epinions1": DatasetInfo(
        "soc-Epinions1",
        "https://snap.stanford.edu/data/soc-Epinions1.txt.gz",
        True,
        "Red de confianza de Epinions.com (75k nodos, 508k aristas)",
    ),

    # Red de confianza/desconfianza con signo de Epinions.com.
    # Nodos = usuarios, aristas dirigidas con etiqueta +1 (trust) o -1
    # (distrust). Mucho más grande que soc-Epinions1.
    # Benchmark estándar para análisis de redes con signo, balance
    # estructural y detección de polarización.
    "soc-sign-epinions": DatasetInfo(
        "soc-sign-epinions",
        "https://snap.stanford.edu/data/soc-sign-epinions.txt.gz",
        True,
        "Red de confianza firmada de Epinions (131k nodos, 841k aristas)",
    ),

    # Círculos sociales de Twitter: ego-networks de usuarios públicos.
    # Nodos = usuarios, aristas dirigidas = "A sigue a B".
    # Datos: listas de círculos (grupos de seguidos), atributos de perfil
    # anonimizados. Mucho más grande que ego-Facebook. Útil para analizar
    # asimetría del seguimiento, influencia y detección de comunidades
    # en grafos dirigidos de gran escala.
    "ego-Twitter": DatasetInfo(
        "ego-Twitter",
        "https://snap.stanford.edu/data/twitter_combined.txt.gz",
        True,
        "Círculos sociales de Twitter (81k nodos, 1.7M aristas)",
    ),
}


class SNAPDownloader:
    """Gestor de descarga y carga de datasets SNAP.

    Tres responsabilidades:
      1. Descargar el `.txt.gz` desde snap.stanford.edu si no está cacheado.
      2. Descomprimirlo a `.txt` para evitar pagar gzip cada lectura.
      3. Cargar el `.txt` como grafo de NetworkX (`Graph` o `DiGraph`).

    El cacheado es la clave: descargar `web-Google` (5M aristas) tarda
    bastante. Mantener todo en `cache_dir` permite reusar entre runs.

    Attributes:
        cache_dir: Carpeta donde viven los `.gz` y `.txt`.
        verbose: Si True, imprime el progreso de descarga/descompresión.
    """

    def __init__(
        self, cache_dir: str | Path, verbose: bool = True
    ) -> None:
        """Crea el downloader y asegura la existencia de `cache_dir`.

        Args:
            cache_dir: Carpeta donde se guardarán los datasets.
            verbose: Si True, emite mensajes de progreso por stdout.
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

    def _log(self, msg: str) -> None:
        """Imprime `msg` por stdout si `self.verbose`.

        Args:
            msg: Mensaje a emitir.
        """
        # Centralizar el `print` evita esparcir `if verbose:` por todo el código.
        if self.verbose:
            print(msg)

    def _paths(self, name: str) -> tuple[Path, Path]:
        """Devuelve las rutas locales asociadas a un dataset.

        Args:
            name: Clave del dataset en `SNAP_CATALOG`.

        Returns:
            Tupla `(gz_path, txt_path)` con las rutas del fichero comprimido
            y del fichero descomprimido respectivamente.
        """
        # Helper que devuelve las dos rutas asociadas a un dataset:
        # el .gz original (descarga) y el .txt descomprimido (lectura rápida).
        gz_path = self.cache_dir / f"raw/{name}.txt.gz"
        txt_path = self.cache_dir / f"processed/{name}.txt"
        gz_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        return gz_path, txt_path

    @staticmethod
    def list_available() -> list[str]:
        """Lista los nombres de datasets disponibles en el catálogo.

        Returns:
            Lista ordenada alfabéticamente con las claves de `SNAP_CATALOG`.
        """
        # Devuelve los nombres del catálogo ordenados
        return sorted(SNAP_CATALOG.keys())

    @staticmethod
    def describe(name: str) -> str:
        """Devuelve una descripción humana del dataset.

        Args:
            name: Clave del dataset en `SNAP_CATALOG`.

        Returns:
            String multilínea con tipo (dirigido/no dirigido), descripción
            y URL del dataset.

        Raises:
            KeyError: Si `name` no está en `SNAP_CATALOG`.
        """
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
        """Descarga (y opcionalmente descomprime) uno o varios datasets.

        Args:
            names: Un string o un iterable de strings con nombres del catálogo.
            force: Si True, re-descarga aunque el fichero exista. Útil si el
                dataset ha cambiado en el origen.
            decompress: Si True, descomprime el `.gz` a `.txt` y devuelve la
                ruta del `.txt`; si False, devuelve la del `.gz`.

        Returns:
            Diccionario `{nombre: ruta_final}` con la ruta producida para
            cada dataset solicitado.

        Raises:
            KeyError: Si algún `name` no está en `SNAP_CATALOG`.
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
                # Reporta tamaño en MB para feedback al usuario.
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

    def load_as_networkx(
        self,
        name: str,
        rng: random.Random,
        directed: bool | None = None,
    ) -> nx.Graph:
        """Carga el dataset como grafo de NetworkX, aplicando conversión si es necesario.

        Si `directed` es `None` se respeta la dirección natural del catálogo.
        Si difiere, convierte: dirigido→no dirigido colapsa aristas; no dirigido→dirigido
        asigna orientación proporcional al grado de los nodos.

        Args:
            name: Clave del dataset en `SNAP_CATALOG`.
            directed: Si True/False fuerza el tipo de grafo resultante. None = natural.
            rng: Generador aleatorio, requerido solo cuando se convierte no dirigido→dirigido.

        Returns:
            `nx.Graph` o `nx.DiGraph` con los nodos como `int`.

        Raises:
            KeyError: Si `name` no está en `SNAP_CATALOG`.
        """
        if name not in SNAP_CATALOG:
            raise KeyError(f"Dataset '{name}' no está en el catálogo.")

        paths = self.download(name, decompress=True)
        txt_path = paths[name]
        info = SNAP_CATALOG[name]

        create_using = nx.DiGraph if info.directed else nx.Graph
        graph: nx.Graph = nx.read_edgelist(
            txt_path, comments="#", create_using=create_using(), nodetype=int
        )

        want_directed = info.directed if directed is None else directed
        if info.directed and not want_directed:
            graph = nx.Graph(graph)
        elif not info.directed and want_directed:
            graph = SNAPDownloader._ba_to_directed_prob(graph, rng)
        return graph

    @staticmethod
    def _ba_to_directed_prob(graph: nx.Graph, rng: random.Random) -> nx.DiGraph:
        """Convierte un grafo no dirigido a dirigido orientando cada arista
        según los grados: la probabilidad de que `v` sea destino es deg(v)/(deg(u)+deg(v)).

        Args:
            graph: Grafo no dirigido de entrada.
            rng: Generador aleatorio para la orientación.

        Returns:
            DiGraph con los mismos nodos y una dirección por arista.
        """
        dg = nx.DiGraph()
        dg.add_nodes_from(graph.nodes())
        for u, v in graph.edges():
            deg_u = graph.degree(u)
            deg_v = graph.degree(v)
            total = deg_u + deg_v
            if rng.random() < deg_v / total:
                dg.add_edge(u, v)
            else:
                dg.add_edge(v, u)
        return dg

    @staticmethod
    def _download_file(url: str, dest: Path) -> None:
        """Descarga `url` a `dest` haciendo streaming a disco.

        Args:
            url: URL absoluta del recurso a descargar.
            dest: Ruta local de destino.
        """
        # Helper estático y privado (`_`). Hace una sola cosa: bajar bytes.
        # User-Agent falso porque SNAP rechaza el de urllib por defecto
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
        """Descomprime un fichero gzip mediante streaming.

        Args:
            src: Ruta al fichero `.gz` de origen.
            dest: Ruta del fichero descomprimido de destino.
        """
        # Mismo patrón: streaming, sin cargar todo en memoria.
        # `gzip.open(..., "rb")` te da un file-like binario que descomprime al vuelo.
        with gzip.open(src, "rb") as f_in, open(dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


class SNAPGraph(BaseGraph):
    """Adaptador de un dataset SNAP a la interfaz `BaseGraph`.

    Composición sobre herencia: `SNAPGraph` NO hereda de `SNAPDownloader`,
    sino que tiene uno como atributo (`self.downloader`). Así separamos:
      - `SNAPDownloader` = lógica de I/O (descarga, caché, parsing).
      - `SNAPGraph`      = adaptador a la interfaz del proyecto.

    Attributes:
        dataset_name: Clave del catálogo (p.ej. "ca-GrQc").
        cache_dir: Carpeta de caché. Por defecto vive bajo `src/data/snap`.
        downloader: Instancia de `SNAPDownloader` que hace el trabajo real.
        seed: Heredado de `BaseGraph`. SNAP no usa seeds (los grafos son
            fijos), pero respetamos la firma común.
    """

    def __init__(
        self,
        dataset_name: str,
        cache_dir: str | Path = "./data/snap",
        directed: bool | None = None,
        seed: int | None = None,
        layer: Layer = Layer.ANALOG,
    ) -> None:
        """Inicializa el adaptador SNAP.

        Args:
            dataset_name: Clave del dataset en `SNAP_CATALOG`.
            cache_dir: Carpeta donde se cacheará el dataset.
            directed: Si True/False fuerza el tipo de grafo. None = natural del catálogo.
            seed: Semilla (no usada en la topología, sí en la anotación de trust).
            layer: Capa asignada a todas las aristas.
        """
        super().__init__(seed=seed, layer=layer)
        self.dataset_name = dataset_name
        self.cache_dir = cache_dir
        self.directed = directed
        # Composición: delega toda la lógica de descarga al downloader.
        self.downloader = SNAPDownloader(cache_dir=cache_dir, verbose=True)

    def _build_topology(self) -> nx.Graph:
        """Construye la topología SNAP desnuda.

        Returns:
            Grafo `nx.Graph` o `nx.DiGraph` correspondiente al dataset.
        """
        rng = random.Random(self.seed)
        return self.downloader.load_as_networkx(
            self.dataset_name, directed=self.directed, rng=rng
        )


if __name__ == "__main__":
    downloader = SNAPDownloader(cache_dir="./data/snap", verbose=True)
    names = downloader.list_available()
    print(f"Descargando {len(names)} datasets: {names}\n")
    for name in names:
        try:
            downloader.download(name)
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {name}: {exc}")
    print("\nDescarga completada.")
