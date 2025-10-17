"""
Service de recherche bibliographique multi-sources.

Ce service unifie les recherches sur BnF, Google Books et OpenLibrary
en utilisant différentes stratégies et en fusionnant les résultats.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

# Import des services existants
from .bnf_service import BnfBook, BnfService
from .googlebooks_service import GoogleBooksService
from .openlibrary_service import OpenLibraryService

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entrée de cache avec TTL."""

    data: list[UnifiedBookResult]
    created_at: datetime
    ttl_hours: int = 24

    @property
    def is_expired(self) -> bool:
        """Vérifie si l'entrée a expiré."""
        return datetime.now() > self.created_at + timedelta(hours=self.ttl_hours)


class SimpleCache:
    """Cache mémoire simple avec TTL."""

    def __init__(self):
        self._cache: dict[str, CacheEntry] = {}

    def get(self, key: str) -> list[UnifiedBookResult] | None:
        """Récupère une entrée du cache si elle existe et n'est pas expirée."""
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            return entry.data
        elif entry:
            # Nettoie l'entrée expirée
            del self._cache[key]
        return None

    def set(self, key: str, data: list[UnifiedBookResult]) -> None:
        """Stocke une entrée dans le cache."""
        self._cache[key] = CacheEntry(data=data, created_at=datetime.now())

    def clear(self) -> None:
        """Vide le cache."""
        self._cache.clear()


_global_cache = SimpleCache()


@dataclass(slots=True)
class _SourceMetric:
    """Métriques d'exécution d'une source."""

    source: str
    started: float
    ended: float = 0.0
    status: str = "success"  # success | timeout | error
    results_count: int = 0
    error: str = ""

    @property
    def duration_ms(self) -> int:
        """Durée en millisecondes, bornée à 0 si non terminée."""
        end = self.ended if self.ended else time.perf_counter()
        return int(max(0.0, (end - self.started)) * 1000)


@dataclass
class SearchSourceInfo:
    """Métadonnées sur la source de recherche."""

    name: str  # "BnF", "Google Books", "OpenLibrary"
    confidence: float  # 0.0 - 1.0
    response_time: float  # en secondes
    success: bool = True


@dataclass
class UnifiedBookResult:
    """Format unifié pour tous les résultats de recherche."""

    # Champs OBLIGATOIRES d'abord
    title: str
    source: SearchSourceInfo

    # Champs OPTIONNELS ensuite (avec valeurs par défaut)
    subtitle: str | None = None
    authors: list[str] = field(default_factory=list)
    main_author: str | None = None

    # Métadonnées
    isbn: str | None = None
    year: str | None = None
    publisher: str | None = None
    collection: str | None = None

    # Descriptions
    description: str | None = None
    summary: str | None = None

    # Images
    thumbnail_url: str | None = None
    cover_image_url: str | None = None

    # Données techniques
    raw_data: dict = field(default_factory=dict)

    # Score calculé pour le tri
    _score: float = field(default=0.0, init=False)

    def _calculate_quality_score(self) -> float:
        """Calcule un score de qualité basé sur la complétude des données."""
        score = 0.0

        # Score de base selon la source (fiabilité)
        source_scores = {
            "BnF": 1.0,  # Le plus fiable
            "Google Books": 0.8,  # Très bon
            "OpenLibrary": 0.6,  # Correct
        }
        score += source_scores.get(self.source.name, 0.5) * 30

        # Bonus pour chaque champ rempli
        fields_bonus = {
            "title": 10,
            "authors": 8 if self.authors else 0,
            "main_author": 5 if self.main_author else 0,
            "isbn": 8 if self.isbn else 0,
            "year": 5 if self.year else 0,
            "publisher": 4 if self.publisher else 0,
            "description": 6 if self.description else 0,
            "summary": 4 if self.summary else 0,
            "thumbnail_url": 3 if self.thumbnail_url else 0,
        }

        score += sum(fields_bonus.values())

        # Pénalité pour temps de réponse lent
        if self.source.response_time > 5.0:
            score -= 5

        # Bonus pour confiance de la source
        score += self.source.confidence * 10

        return min(100.0, max(0.0, score))

    @property
    def score(self) -> float:
        """Score de qualité du résultat (0-100)."""
        return self._score

    @property
    def display_title(self) -> str:
        """Titre d'affichage avec sous-titre si disponible."""
        if self.subtitle:
            return f"{self.title}: {self.subtitle}"
        return self.title

    @property
    def authors_display(self) -> str:
        """Auteurs formatés pour affichage."""
        if not self.authors:
            return self.main_author or "Auteur inconnu"
        return ", ".join(self.authors[:3]) + ("..." if len(self.authors) > 3 else "")

    @property
    def year_display(self) -> str:
        """Année formatée pour affichage."""
        return self.year or "Année inconnue"

    def __post_init__(self):
        """Calcule le score de qualité du résultat."""
        self._score = self._calculate_quality_score()


class SearchSource(Enum):
    """Sources de recherche disponibles."""

    BNF = "BnF"
    GOOGLE_BOOKS = "Google Books"
    OPENLIBRARY = "OpenLibrary"


class SearchResultAdapter:
    """Convertit les résultats des différents services vers UnifiedBookResult."""

    @staticmethod
    def from_bnf_book(bnf_book: BnfBook, source_info: SearchSourceInfo) -> UnifiedBookResult:
        """Convertit un BnfBook vers UnifiedBookResult."""
        return UnifiedBookResult(
            title=bnf_book.titre,
            subtitle=bnf_book.sous_titre,
            authors=bnf_book.auteurs,
            main_author=bnf_book.auteurs[0] if bnf_book.auteurs else None,
            isbn=bnf_book.isbn,
            year=bnf_book.date_publication,
            publisher=bnf_book.editeur,
            collection=bnf_book.collection,
            source=source_info,
            raw_data={"type": "BnfBook", "original": bnf_book.__dict__},
        )

    @staticmethod
    def from_ext_book(ext_book, source_info: SearchSourceInfo) -> UnifiedBookResult:
        """Convertit un ExtBook vers UnifiedBookResult."""

        # DEBUG: Afficher les données brutes
        logger.debug("🔍 DEBUG OpenLibrary raw data:")
        logger.debug(f"✅  ext_book.titre: '{ext_book.titre}'")
        logger.debug(f"✅  ext_book.auteurs: {ext_book.auteurs}")
        logger.debug(f"✅  ext_book.isbn: '{ext_book.isbn}'")
        logger.debug(f"✅  ext_book.editeur: '{ext_book.editeur}'")
        logger.debug(f"✅  ext_book.date_publication: '{ext_book.date_publication}'")  # ✅ Bon nom
        logger.debug(f"✅  ext_book.sous_titre: '{ext_book.sous_titre}'")  # ✅ Bon nom
        logger.debug(f"✅  ext_book.collection: '{ext_book.collection}'")

        return UnifiedBookResult(
            title=ext_book.titre,
            source=source_info,
            subtitle=ext_book.sous_titre,
            authors=ext_book.auteurs,
            main_author=ext_book.auteurs[0] if ext_book.auteurs else None,
            isbn=ext_book.isbn,
            year=str(ext_book.date_publication) if ext_book.date_publication else None,
            publisher=ext_book.editeur,
            collection=ext_book.collection,
        )

    @staticmethod
    def from_google_books(google_data: dict, source_info: SearchSourceInfo) -> UnifiedBookResult:
        """Convertit les données Google Books vers UnifiedBookResult."""
        volume_info = google_data.get("volumeInfo", {})

        # Extraction de l'ISBN depuis industryIdentifiers
        isbn = None
        for identifier in volume_info.get("industryIdentifiers", []):
            if identifier.get("type") in ["ISBN_13", "ISBN_10"]:
                isbn = identifier.get("identifier")
                break

        return UnifiedBookResult(
            title=volume_info.get("title", "Titre inconnu"),
            subtitle=volume_info.get("subtitle"),
            authors=volume_info.get("authors", []),
            main_author=volume_info.get("authors", [None])[0],
            isbn=isbn,
            year=volume_info.get("publishedDate", "").split("-")[0]
            if volume_info.get("publishedDate")
            else None,
            publisher=volume_info.get("publisher"),
            description=volume_info.get("description"),
            thumbnail_url=volume_info.get("imageLinks", {}).get("thumbnail"),
            source=source_info,
            raw_data={"type": "GoogleBooks", "original": google_data},
        )


# ==================== STRATEGIES PATTERN ====================


class SearchStrategy(ABC):
    """Interface abstraite pour les stratégies de recherche."""

    @abstractmethod
    def search_by_isbn(self, isbn: str, services: dict[str, any]) -> list[UnifiedBookResult]:
        """Recherche par ISBN selon la stratégie."""
        pass

    @abstractmethod
    def search_by_title_author(
        self, title: str, author: str, services: dict[str, any]
    ) -> list[UnifiedBookResult]:
        """Recherche par titre/auteur selon la stratégie."""
        pass


class SequentialSearchStrategy(SearchStrategy):
    """Recherche séquentielle: BnF → Google Books → OpenLibrary (stop au premier succès)."""

    def search_by_isbn(self, isbn: str, services: dict[str, any]) -> list[UnifiedBookResult]:
        """Recherche séquentielle par ISBN."""
        results = []

        # Ordre de priorité: BnF, Google Books, OpenLibrary
        search_order = [
            ("BnF", services.get("bnf")),
            ("Google Books", services.get("google")),
            ("OpenLibrary", services.get("openlibrary")),
        ]

        for source_name, service in search_order:
            if not service:
                continue

            logger.info(f"✅ Recherche séquentielle ISBN sur {source_name}")
            start_time = time.time()

            try:
                if source_name == "BnF":
                    bnf_books = service.search_by_isbn(isbn)
                    response_time = time.time() - start_time

                    for bnf_book in bnf_books:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.95,  # BnF très fiable
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_bnf_book(bnf_book, source_info)
                        results.append(result)

                elif source_name == "OpenLibrary":
                    ext_book = service.search_by_isbn(isbn)
                    if ext_book:
                        response_time = time.time() - start_time
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.75,  # Moins fiable que BnF
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_ext_book(ext_book, source_info)
                        results.append(result)

                elif source_name == "Google Books":
                    google_books = service.search_by_isbn(isbn)  # Cette méthode existe déjà !
                    response_time = time.time() - start_time

                    for book in google_books:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.85,  # Entre BnF et OpenLibrary
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_google_books(book, source_info)
                        results.append(result)
                        # Si on a des résultats, on s'arrête (stratégie séquentielle)
                if results:
                    logger.info(
                        f"✅ Trouvé {len(results)} résultats sur {source_name}, arrêt de la recherche"
                    )
                    break

            except Exception as e:
                response_time = time.time() - start_time
                logger.info(f"❌ Erreur recherche {source_name}: {e}")
                # On continue avec le service suivant
                continue

        return results

    def search_by_title_author(
        self, title: str, author: str, services: dict[str, any]
    ) -> list[UnifiedBookResult]:
        """Recherche séquentielle par titre/auteur."""
        results = []

        search_order = [
            ("BnF", services.get("bnf")),
            ("OpenLibrary", services.get("openlibrary")),
            ("Google Books", services.get("google")),
        ]

        for source_name, service in search_order:
            if not service:
                continue

            logger.info(f"✅ Recherche séquentielle titre/auteur sur {source_name}")
            start_time = time.time()
            logger.info(f"✅ Services disponibles: {list(services.keys())}")
            logger.info(f"✅ Google Books activé: {'google' in services}")
            logger.info(f"✅ Service Google: {services.get('google')}")
            try:
                if source_name == "BnF":
                    bnf_books = service.search_by_title_author(title, author)
                    response_time = time.time() - start_time

                    for bnf_book in bnf_books:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.90,  # Un peu moins fiable que ISBN
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_bnf_book(bnf_book, source_info)
                        results.append(result)

                elif source_name == "OpenLibrary":
                    ext_books = service.search_by_title(
                        title
                    )  # OpenLibrary n'a pas search_by_title_author
                    response_time = time.time() - start_time

                    for ext_book in ext_books:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.70,  # Moins précis sans auteur
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_ext_book(ext_book, source_info)
                        results.append(result)
                elif source_name == "Google Books":
                    google_books = service.search_by_title_author(title, author)
                    response_time = time.time() - start_time

                    for book in google_books:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.80,  # Entre BnF et OpenLibrary
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_google_books(book, source_info)
                        results.append(result)

                # Si on a des résultats, on s'arrête
                if results:
                    logger.info(
                        f"✅ Trouvé {len(results)} résultats sur {source_name}, arrêt de la recherche"
                    )
                    break

            except Exception as e:
                logger.error(f"❌ Erreur recherche {source_name}: {e}")
                continue

        return results


# ==================== CLASSE PRINCIPALE ====================


class MetaSearchService:
    """
    Service de recherche bibliographique multi-sources.

    Coordonne les recherches sur BnF, Google Books et OpenLibrary
    avec différentes stratégies et un système de cache.
    """

    def __init__(self, strategy: SearchStrategy = None):
        """
        Initialize le MetaSearchService.

        Args:
            strategy: Stratégie de recherche (par défaut: SequentialSearchStrategy)
        """
        self.strategy = strategy or SequentialSearchStrategy()

        # Initialisation des services
        self.services = {
            "bnf": BnfService(),
            "google": GoogleBooksService(),
            "openlibrary": OpenLibraryService(),
        }

        # Cache simple en mémoire (ISBN -> List[UnifiedBookResult])
        self._isbn_cache: dict[str, list[UnifiedBookResult]] = {}
        self._title_cache: dict[str, list[UnifiedBookResult]] = {}

        logger.info(f"✅ MetaSearchService initialisé avec {type(self.strategy).__name__}")

    def search_by_isbn(self, isbn: str, use_cache: bool = True) -> list[UnifiedBookResult]:
        """
        Recherche un livre par ISBN.

        Args:
            isbn: Numéro ISBN à rechercher
            use_cache: Si True, utilise le cache local

        Returns:
            Liste des résultats unifiés, triés par score de qualité
        """
        if not isbn or not isbn.strip():
            return []

        isbn_clean = isbn.strip().replace("-", "").replace(" ", "")

        # Vérifier le cache
        if use_cache and isbn_clean in self._isbn_cache:
            logger.info(f"✅ Résultat ISBN {isbn_clean} trouvé dans le cache")
            return self._isbn_cache[isbn_clean]

        # Recherche via la stratégie
        logger.info(f"✅ Recherche ISBN {isbn_clean} via {type(self.strategy).__name__}")
        results = self.strategy.search_by_isbn(isbn_clean, self.services)

        # Trier par score de qualité (décroissant)
        results.sort(key=lambda r: r.score, reverse=True)

        # Mettre en cache
        if use_cache:
            self._isbn_cache[isbn_clean] = results

        logger.info(f"✅ Trouvé {len(results)} résultats pour ISBN {isbn_clean}")
        return results

    def search_by_title_author(
        self, title: str, author: str = "", use_cache: bool = True
    ) -> list[UnifiedBookResult]:
        """
        Recherche un livre par titre et auteur.

        Args:
            title: Titre du livre
            author: Auteur du livre (optionnel)
            use_cache: Si True, utilise le cache local

        Returns:
            Liste des résultats unifiés, triés par score de qualité
        """
        if not title or not title.strip():
            return []

        cache_key = f"{title.strip().lower()}:{author.strip().lower()}"

        # Vérifier le cache
        if use_cache and cache_key in self._title_cache:
            logger.info("✅ Résultat titre/auteur trouvé dans le cache")
            return self._title_cache[cache_key]

        # Recherche via la stratégie
        logger.info(
            f"✅ Recherche titre '{title}' auteur '{author}' via {type(self.strategy).__name__}"
        )
        results = self.strategy.search_by_title_author(title.strip(), author.strip(), self.services)

        # Trier par score de qualité (décroissant)
        results.sort(key=lambda r: r.score, reverse=True)

        # Mettre en cache
        if use_cache:
            self._title_cache[cache_key] = results

        logger.info(f"✅ Trouvé {len(results)} résultats pour titre '{title}'")
        return results

    def clear_cache(self):
        """Vide le cache de recherche."""
        self._isbn_cache.clear()
        self._title_cache.clear()
        logger.info("✅ Cache vidé")

    def get_cache_stats(self) -> dict[str, int]:
        """Retourne les statistiques du cache."""
        return {"isbn_entries": len(self._isbn_cache), "title_entries": len(self._title_cache)}

    def set_strategy(self, strategy: SearchStrategy):
        """Change la stratégie de recherche."""
        self.strategy = strategy
        logger.info(f"✅ Stratégie changée vers {type(strategy).__name__}")


# ==================== STRATÉGIES AVANCÉES ====================


class ParallelSearchStrategy(SearchStrategy):
    """Stratégie parallèle avec timeouts globaux et par source."""

    def __init__(
        self,
        timeout: float = 5.0,
        max_workers: int = 3,
        source_timeouts: dict[str, float] | None = None,
    ) -> None:
        """Initialise la stratégie.

        Args:
            timeout: Timeout global d’attente des futures en secondes.
            max_workers: Nombre maximal de workers du pool threads.
            source_timeouts: Timeouts individuels par source.
        """
        self.timeout = timeout
        self.max_workers = max_workers
        self.source_timeouts = source_timeouts or {
            "BnF": 3.0,
            "OpenLibrary": 4.0,
            "Google Books": 3.0,
        }
        self.cache = _global_cache
        logger.debug("✅  META SEARCH SERVICE LOADED")

    @property
    def duration_ms(self) -> int:
        return int((self.ended - self.started) * 1000)

    def search_by_isbn(self, isbn: str, services: dict[str, any]) -> list[UnifiedBookResult]:
        """Recherche parallèle par ISBN avec cache."""
        # 🆕 Vérifier le cache d'abord
        cache_key = f"isbn:{isbn}"
        cached_results = self.cache.get(cache_key)
        if cached_results:
            logger.info("💾 Cache HIT pour ISBN %s • %d résultat(s)", isbn, len(cached_results))
            return cached_results

        logger.info("🔍 Cache MISS pour ISBN %s • recherche en cours", isbn)

        results = []

        # Préparer les tâches de recherche
        search_tasks = []

        if services.get("bnf"):
            search_tasks.append(("BnF", services["bnf"], "search_by_isbn", isbn))
        if services.get("openlibrary"):
            search_tasks.append(("OpenLibrary", services["openlibrary"], "search_by_isbn", isbn))
        if services.get("google"):
            search_tasks.append(("Google Books", services["google"], "search_by_isbn", isbn))

        # Exécution parallèle
        metrics: dict[str, _SourceMetric] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_source = {}
            for source_name, service, method_name, query in search_tasks:
                metrics[source_name] = _SourceMetric(
                    source=source_name, started=time.perf_counter()
                )
                fut = executor.submit(
                    self._search_single_source, source_name, service, method_name, query
                )
                future_to_source[fut] = source_name

            logger.debug("🕐 Démarrage wait() avec timeout=%ss", self.timeout)
            done, not_done = concurrent.futures.wait(future_to_source.keys(), timeout=self.timeout)
            logger.debug("🕐 Fin wait() - done:%d not_done:%d", len(done), len(not_done))

            for fut in done:
                source_name = future_to_source[fut]
                m = metrics[source_name]  # ✅ Assigner m d'abord !
                try:
                    value = fut.result()
                    # Accepte soit [UnifiedBookResult,...], soit ( [UnifiedBookResult,...], <info> )
                    if isinstance(value, tuple):
                        source_results = value[0]
                    else:
                        source_results = value
                    m.ended = time.perf_counter()
                    m.results_count = len(source_results) if source_results else 0
                    m.status = "success"
                    logger.info(
                        "✅ %s • %d ms • %d résultat(s)",
                        source_name,
                        m.duration_ms,
                        m.results_count,
                    )
                    if source_results:
                        results.extend(source_results)
                except Exception as exc:
                    m.ended = time.perf_counter()
                    m.status = "error"
                    m.error = str(exc)
                    logger.error("❌ %s • %d ms • erreur: %s", source_name, m.duration_ms, m.error)

            for fut in not_done:
                source_name = future_to_source[fut]
                m = metrics[source_name]

                # Tentative d'annulation avec vérification
                try:
                    was_cancelled = fut.cancel()
                    if was_cancelled:
                        logger.debug("🚫 %s • Annulation réussie", source_name)
                    else:
                        logger.debug(
                            "⚠️ %s • Annulation impossible (tâche déjà en cours)", source_name
                        )
                except Exception as e:
                    logger.warning("❌ %s • Erreur lors de l'annulation: %s", source_name, e)

                m.ended = m.started + self.timeout
                m.status = "timeout"
                logger.info(
                    "⏱️ %s • %d ms • timeout après %ss", source_name, m.duration_ms, self.timeout
                )

        # Résumé agrégé de la recherche
        if metrics:
            started_min = min(m.started for m in metrics.values())
            ended_max = max((m.ended or m.started) for m in metrics.values())
            total_ms = int((ended_max - started_min) * 1000)
            ok = sum(1 for m in metrics.values() if m.status == "success")
            to = sum(1 for m in metrics.values() if m.status == "timeout")
            er = sum(1 for m in metrics.values() if m.status == "error")
            logger.info(
                "📊 Résumé • %d ms • ok:%d timeout:%d erreur:%d • total:%d résultat(s)",
                total_ms,
                ok,
                to,
                er,
                len(results),
            )

        if results:
            self.cache.set(cache_key, results)
            logger.info("💾 Résultats mis en cache pour ISBN %s", isbn)

        return results

    def search_by_title_author(
        self, title: str, author: str, services: dict[str, any]
    ) -> list[UnifiedBookResult]:
        """Recherche parallèle par titre et auteur avec cache."""
        start_time = time.perf_counter()
        # 🆕 Vérifier le cache d'abord
        cache_key = f"title_author:{title.lower()}:{author.lower()}"
        cached_results = self.cache.get(cache_key)
        if cached_results:
            cache_time = (time.perf_counter() - start_time) * 1000
            logger.info("💾 Cache HIT • %.1fms", cache_time)
            return cached_results

        logger.info("🔍 Cache MISS pour '%s' par '%s' • recherche en cours", title, author)

        setup_start = time.perf_counter()
        results = []

        search_tasks = []

        if services.get("bnf"):
            logger.info("✅ BnF ajouté aux tâches")
            search_tasks.append(("BnF", services["bnf"], "search_by_title_author", (title, author)))
        if services.get("openlibrary"):
            logger.info("✅ OpenLibrary ajouté aux tâches")
            search_tasks.append(("OpenLibrary", services["openlibrary"], "search_by_title", title))
        if services.get("google"):
            logger.info("✅ Google Books ajouté aux tâches")
            search_tasks.append(
                ("Google Books", services["google"], "search_by_title_author", (title, author))
            )
        else:
            logger.error("❌ Google Books NOT FOUND dans services")

        logger.info(f"✅ Nombre de tâches créées: {len(search_tasks)}")
        setup_time = (time.perf_counter() - setup_start) * 1000
        metrics: dict[str, _SourceMetric] = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_source = {}
            for source_name, service, method_name, query in search_tasks:
                metrics[source_name] = _SourceMetric(
                    source=source_name, started=time.perf_counter()
                )
                fut = executor.submit(
                    self._search_single_source, source_name, service, method_name, query
                )
                future_to_source[fut] = source_name

            logger.debug("🕐 Démarrage wait() avec timeout=%ss", self.timeout)
            done, not_done = concurrent.futures.wait(future_to_source.keys(), timeout=self.timeout)
            logger.debug("🕐 Fin wait() - done:%d not_done:%d", len(done), len(not_done))

            for fut in done:
                source_name = future_to_source[fut]
                m = metrics[source_name]  # ✅ Assigner m d'abord !
                try:
                    value = fut.result()
                    # Accepte soit [UnifiedBookResult,...], soit ( [UnifiedBookResult,...], <info> )
                    if isinstance(value, tuple):
                        source_results = value[0]
                    else:
                        source_results = value
                    m.ended = time.perf_counter()
                    m.results_count = len(source_results) if source_results else 0
                    m.status = "success"
                    logger.info(
                        "✅ %s • %d ms • %d résultat(s)",
                        source_name,
                        m.duration_ms,
                        m.results_count,
                    )
                    if source_results:
                        results.extend(source_results)
                except Exception as exc:
                    m.ended = time.perf_counter()
                    m.status = "error"
                    m.error = str(exc)
                    logger.error("❌ %s • %d ms • erreur: %s", source_name, m.duration_ms, m.error)

            for fut in not_done:
                source_name = future_to_source[fut]
                m = metrics[source_name]

                # Tentative d'annulation avec vérification
                try:
                    was_cancelled = fut.cancel()
                    if was_cancelled:
                        logger.debug("🚫 %s • Annulation réussie", source_name)
                    else:
                        logger.debug(
                            "⚠️ %s • Annulation impossible (tâche déjà en cours)", source_name
                        )
                except Exception as e:
                    logger.warning("❌ %s • Erreur lors de l'annulation: %s", source_name, e)

                m.ended = m.started + self.timeout
                m.status = "timeout"
                logger.info(
                    "⏱️ %s • %d ms • timeout après %ss", source_name, m.duration_ms, self.timeout
                )

        # Résumé agrégé
        if metrics:
            started_min = min(m.started for m in metrics.values())
            ended_max = max((m.ended or m.started) for m in metrics.values())
            total_ms = int((ended_max - started_min) * 1000)
            ok = sum(1 for m in metrics.values() if m.status == "success")
            to = sum(1 for m in metrics.values() if m.status == "timeout")
            er = sum(1 for m in metrics.values() if m.status == "error")
            logger.info(
                "📊 Résumé • %d ms • ok:%d timeout:%d erreur:%d • total:%d résultat(s)",
                total_ms,
                ok,
                to,
                er,
                len(results),
            )

        if results:
            cache_start = time.perf_counter()
            self.cache.set(cache_key, results)
            cache_time = (time.perf_counter() - cache_start) * 1000
            logger.info("💾 Cache set • %.1fms", cache_time)

        # 📊 PROFILING - Total
        total_time = (time.perf_counter() - start_time) * 1000
        logger.info(
            "⏱️ PROFIL total • %.1fms (setup:%.1f cache:%.1f)",
            total_time,
            setup_time,
            cache_time if results else 0.0,
        )

        return results

    def _search_single_source(
        self, source_name: str, service, method_name: str, query
    ) -> list[UnifiedBookResult]:
        """Effectue la recherche sur une source unique."""
        results = []
        start_time = time.time()

        try:
            logger.debug(f"✅ SOURCE: {source_name}")
            logger.debug(f"✅ METHOD: {method_name}")

            # ========================================
            # ARCHITECTURE PARFAITE PAR method_name
            # ========================================

            if method_name == "search_by_isbn":
                # ISBN - Tous les services supportés
                if source_name == "BnF":
                    bnf_books = service.search_by_isbn(query)
                    response_time = time.time() - start_time
                    for bnf_book in bnf_books:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.95,
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_bnf_book(bnf_book, source_info)
                        results.append(result)

                elif source_name == "OpenLibrary":
                    ext_book = service.search_by_isbn(query)
                    response_time = time.time() - start_time
                    if ext_book:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.75,
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_ext_book(ext_book, source_info)
                        results.append(result)

                elif source_name == "Google Books":
                    book_dto = service.search_by_isbn(query)
                    response_time = time.time() - start_time
                    if book_dto:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.80,
                            response_time=response_time,
                            success=True,
                        )
                        # Convertir BookDTO vers dict pour SearchResultAdapter
                        google_data = {
                            "volumeInfo": {
                                "title": book_dto.title,
                                "authors": [book_dto.authors_text] if book_dto.authors_text else [],
                                "publisher": book_dto.publisher,
                                "publishedDate": book_dto.year,
                                "industryIdentifiers": [
                                    {"type": "ISBN", "identifier": book_dto.isbn}
                                ]
                                if book_dto.isbn
                                else [],
                                "description": book_dto.description,
                            }
                        }
                        result = SearchResultAdapter.from_google_books(google_data, source_info)
                        results.append(result)

            elif method_name == "search_by_title_author":
                # TITLE + AUTHOR - Tous les services supportés
                if source_name == "BnF":
                    title, author = query if isinstance(query, tuple) else (query, None)
                    bnf_books = service.search_by_title_author(title, author)
                    response_time = time.time() - start_time
                    for bnf_book in bnf_books:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.90,
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_bnf_book(bnf_book, source_info)
                        results.append(result)

                elif source_name == "OpenLibrary":
                    title, author = query if isinstance(query, tuple) else (query, None)
                    # OpenLibrary n'a pas search_by_title_author, on utilise search_by_title
                    ext_books = service.search_by_title(title)
                    response_time = time.time() - start_time
                    for ext_book in ext_books:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.65,  # Moins précis sans auteur
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_ext_book(ext_book, source_info)
                        results.append(result)

                elif source_name == "Google Books":
                    title, author = query if isinstance(query, tuple) else (query, None)
                    google_items = service.search_by_title_author(title, author)
                    response_time = time.time() - start_time
                    source_info = SearchSourceInfo(
                        name=source_name,
                        confidence=0.80,
                        response_time=response_time,
                        success=True,
                    )
                    for item in google_items:
                        result = SearchResultAdapter.from_google_books(item, source_info)
                        results.append(result)

            elif method_name == "search_by_title":
                # TITLE ONLY - Tous les services supportés
                if source_name == "BnF":
                    # BnF n'a pas search_by_title seul, on utilise search_by_title_author avec author=None
                    bnf_books = service.search_by_title_author(query, None)
                    response_time = time.time() - start_time
                    for bnf_book in bnf_books:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.85,
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_bnf_book(bnf_book, source_info)
                        results.append(result)

                elif source_name == "OpenLibrary":
                    ext_books = service.search_by_title(query)
                    response_time = time.time() - start_time
                    for ext_book in ext_books:
                        source_info = SearchSourceInfo(
                            name=source_name,
                            confidence=0.70,
                            response_time=response_time,
                            success=True,
                        )
                        result = SearchResultAdapter.from_ext_book(ext_book, source_info)
                        results.append(result)

                elif source_name == "Google Books":
                    # Google Books : utiliser search_by_title_author avec author=None
                    google_items = service.search_by_title_author(query, None)
                    response_time = time.time() - start_time
                    source_info = SearchSourceInfo(
                        name=source_name,
                        confidence=0.75,
                        response_time=response_time,
                        success=True,
                    )
                    for item in google_items:
                        result = SearchResultAdapter.from_google_books(item, source_info)
                        results.append(result)

        except Exception as e:
            logger.error(f"❌ Erreur source {source_name}: {e}")

        return results


class BestResultStrategy(SearchStrategy):
    """Combine séquentiel et parallèle: parallèle d'abord, puis déduplication et scoring."""

    def __init__(self):
        self.parallel_strategy = ParallelSearchStrategy(timeout=5.0)

    def search_by_isbn(self, isbn: str, services: dict[str, any]) -> list[UnifiedBookResult]:
        """Recherche avec déduplication et meilleur scoring."""
        # D'abord recherche parallèle
        results = self.parallel_strategy.search_by_isbn(isbn, services)

        # Déduplication par titre + auteur principal
        deduplicated = self._deduplicate_results(results)

        return deduplicated

    def search_by_title_author(
        self, title: str, author: str, services: dict[str, any]
    ) -> list[UnifiedBookResult]:
        """Recherche avec déduplication et meilleur scoring."""
        results = self.parallel_strategy.search_by_title_author(title, author, services)

        deduplicated = self._deduplicate_results(results)

        return deduplicated

    def _deduplicate_results(self, results: list[UnifiedBookResult]) -> list[UnifiedBookResult]:
        """Déduplique les résultats en gardant le meilleur score."""
        if not results:
            return results

        # Grouper par clé de déduplication (titre + auteur principal)
        groups = {}
        for result in results:
            # 🔧 Vérifications AVANT l'utilisation
            if not hasattr(result, "main_author"):
                logger.info(
                    "❌ Objet sans mainauthor: %s - %s", type(result).__name__, vars(result)
                )
                continue

            logger.debug(
                "🔍 Debug déduplication - type: %s, titre: %s", type(result).__name__, result.title
            )

            key = self._normalize_for_deduplication(result.title, result.main_author or "")
            if key not in groups:
                groups[key] = []
            groups[key].append(result)

        # Garder le meilleur de chaque groupe
        deduplicated = []
        for group_results in groups.values():
            # Trier par score décroissant et prendre le premier
            best = max(group_results, key=lambda r: r.score)

            # Fusion des données: combiner les infos des différentes sources
            merged = self._merge_results(group_results, best)
            deduplicated.append(merged)

        logger.info(f"✅ Déduplication: {len(results)} → {len(deduplicated)} résultats")
        return deduplicated

    def _normalize_for_deduplication(self, title: str, author: str) -> str:
        """Crée une clé normalisée pour la déduplication."""
        import re

        # Normaliser le titre
        title_norm = title.lower().strip()
        title_norm = re.sub(r"[^\w\s]", "", title_norm)  # Supprimer ponctuation
        title_norm = re.sub(r"\s+", " ", title_norm)  # Normaliser espaces

        # Normaliser l'auteur (nom de famille en premier)
        author_norm = author.lower().strip() if author else ""
        # Extraire le nom de famille (dernier mot souvent)
        if author_norm:
            parts = author_norm.split()
            if len(parts) > 1:
                # Mettre nom de famille en premier : "Jean MARTIN" → "martin jean"
                author_norm = f"{parts[-1]} {' '.join(parts[:-1])}"

        return f"{title_norm}|{author_norm}"

    def _merge_results(
        self, group_results: list[UnifiedBookResult], best: UnifiedBookResult
    ) -> UnifiedBookResult:
        """Fusionne les informations de plusieurs résultats."""
        # Partir du meilleur résultat
        merged = best

        # Enrichir avec les données manquantes des autres sources
        for result in group_results:
            if result == best:
                continue

            # Compléter les champs manquants
            if not merged.subtitle and result.subtitle:
                merged.subtitle = result.subtitle
            if not merged.description and result.description:
                merged.description = result.description
            if not merged.summary and result.summary:
                merged.summary = result.summary
            if not merged.thumbnail_url and result.thumbnail_url:
                merged.thumbnail_url = result.thumbnail_url
            if not merged.cover_image_url and result.cover_image_url:
                merged.cover_image_url = result.cover_image_url
            if not merged.publisher and result.publisher:
                merged.publisher = result.publisher
            if not merged.collection and result.collection:
                merged.collection = result.collection

            # Fusionner les auteurs (éviter doublons)
            for author in result.authors:
                if author not in merged.authors:
                    merged.authors.append(author)

        # Recalculer le score après fusion
        merged._score = merged._calculate_quality_score()

        return merged
