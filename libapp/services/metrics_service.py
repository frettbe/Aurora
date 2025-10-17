"""Service de collecte des métriques de performance.

Ce module fournit des décorateurs pour mesurer automatiquement
le temps d'exécution des fonctions critiques.
"""

import functools
import json
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Storage des métriques en mémoire
_metrics_store: dict[str, list[dict]] = defaultdict(list)
_metrics_file = Path("metrics.json")


def benchmark(operation_name: str | None = None) -> Callable:
    """Décorateur pour mesurer le temps d'exécution d'une fonction.

    Usage:
        @benchmark("import_books")
        def import_books_from_csv(filepath):
            ...

    Args:
        operation_name: Nom de l'opération (si None, utilise le nom de la fonction)

    Returns:
        Fonction décorée qui mesure son temps d'exécution
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Nom de l'opération
            op_name = operation_name or func.__name__

            # Mesure du temps
            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                success = False
                error = str(e)
                raise  # Re-raise l'exception
            finally:
                end_time = time.perf_counter()
                duration = end_time - start_time

                # Enregistrer la métrique
                record_metric(
                    operation=op_name,
                    duration=duration,
                    success=success,
                    error=error,
                )

            return result

        return wrapper

    return decorator


def record_metric(
    operation: str,
    duration: float,
    success: bool = True,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Enregistre une métrique de performance.

    Args:
        operation: Nom de l'opération mesurée
        duration: Durée en secondes
        success: Si l'opération a réussi
        error: Message d'erreur (si échec)
        metadata: Données supplémentaires
    """
    metric = {
        "timestamp": datetime.utcnow().isoformat(),
        "operation": operation,
        "duration_ms": round(duration * 1000, 2),
        "success": success,
        "error": error,
        "metadata": metadata or {},
    }

    # Stocker en mémoire
    _metrics_store[operation].append(metric)

    # Logger
    if success:
        logger.info(f"⏱️ {operation} took {metric['duration_ms']}ms")
    else:
        logger.warning(f"⏱️ {operation} FAILED after {metric['duration_ms']}ms: {error}")

    # Sauvegarder périodiquement (tous les 10 enregistrements)
    total_metrics = sum(len(v) for v in _metrics_store.values())
    if total_metrics % 10 == 0:
        save_metrics()


def save_metrics() -> None:
    """Sauvegarde les métriques dans un fichier JSON."""
    try:
        with _metrics_file.open("w", encoding="utf-8") as f:
            json.dump(dict(_metrics_store), f, indent=2)
        logger.debug(f"Metrics saved to {_metrics_file}")
    except Exception as e:
        logger.error(f"Failed to save metrics: {e}")


def get_metrics_summary() -> dict[str, dict]:
    """Retourne un résumé des métriques collectées.

    Returns:
        Dict avec statistiques par opération (count, avg, min, max)
    """
    summary = {}

    for operation, metrics in _metrics_store.items():
        durations = [m["duration_ms"] for m in metrics if m["success"]]

        if durations:
            summary[operation] = {
                "count": len(metrics),
                "success_count": len(durations),
                "avg_ms": round(sum(durations) / len(durations), 2),
                "min_ms": round(min(durations), 2),
                "max_ms": round(max(durations), 2),
            }

    return summary


def export_metrics_csv(filepath: Path) -> None:
    """Exporte les métriques vers un fichier CSV.

    Args:
        filepath: Chemin du fichier CSV de destination
    """
    import csv

    with filepath.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Operation", "Duration (ms)", "Success", "Error"])

        for operation, metrics in _metrics_store.items():
            for metric in metrics:
                writer.writerow(
                    [
                        metric["timestamp"],
                        operation,
                        metric["duration_ms"],
                        metric["success"],
                        metric["error"] or "",
                    ]
                )

    logger.info(f"Metrics exported to {filepath}")
