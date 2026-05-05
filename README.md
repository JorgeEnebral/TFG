# Trabajo Final de Grado

## Interacciones y Dinámicas en la Aldea Global: Modelado Matemático y Psicosocial de la Guerra Cognitiva en Redes Complejas

Autor: Jorge Enebral

Director: David Martín-Corral

---

## Puesta en marcha

### 1. Instalar `uv`

El proyecto usa [uv](https://docs.astral.sh/uv/) como gestor de entornos y dependencias.

**Linux / macOS**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Reinicia el terminal tras la instalación para que `uv` esté en el PATH.

### 2. Instalar dependencias

```bash
make install
```

Esto ejecuta `uv sync`, que crea el entorno virtual en `.venv/` e instala todas las dependencias definidas en `pyproject.toml`.

### 3. Ejecutar la simulación

```bash
# Ejecución por defecto: 12 nodos, 40 pasos, guarda simulation.gif
uv run python src/network_simulation.py

# Parámetros personalizados
uv run python src/network_simulation.py --nodes 30 --time 60

# Ver ventana en vivo (requiere pantalla)
uv run python src/network_simulation.py --show
```

### 4. Comandos útiles del Makefile

| Comando | Descripción |
|---|---|
| `make install` | Crea el entorno e instala dependencias |
| `make clean` | Elimina cachés y archivos temporales |
| `make remove_venv` | Elimina el entorno virtual (incluye `clean`) |
