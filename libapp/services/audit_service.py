"""Service d'audit des actions utilisateur.

Ce module fournit des fonctions pour enregistrer les actions critiques
effectuées dans l'application (CRUD, imports, exports, emprunts).
"""

import json
import logging
from datetime import datetime
from typing import Any

from ..persistence.database import get_session
from ..persistence.models_sa import AuditLog

logger = logging.getLogger(__name__)


class AuditAction:
    """Constantes pour les types d'actions auditées."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    IMPORT = "IMPORT"
    EXPORT = "EXPORT"
    LOAN = "LOAN"
    RETURN = "RETURN"
    SEARCH = "SEARCH"


class AuditEntityType:
    """Constantes pour les types d'entités auditées."""

    BOOK = "book"
    MEMBER = "member"
    LOAN = "loan"


def log_audit(
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    user: str = "system",
    details: dict[str, Any] | None = None,
    level: str = "INFO",
) -> None:
    """Enregistre une action dans le journal d'audit.

    Args:
        action: Type d'action (CREATE, UPDATE, DELETE, etc.)
        entity_type: Type d'entité (book, member, loan)
        entity_id: ID de l'entité (si applicable)
        user: Nom de l'utilisateur (défaut "system")
        details: Détails supplémentaires (dict converti en JSON)
        level: Niveau de log (INFO, WARNING, ERROR)
    """
    try:
        # Convertir details en JSON si présent
        details_json = json.dumps(details) if details else None

        # Créer l'entrée d'audit
        audit_entry = AuditLog(
            timestamp=datetime.utcnow(),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user=user,
            details=details_json,
            level=level,
        )

        # Sauvegarder en base
        with get_session() as session:
            session.add(audit_entry)
            session.commit()

        # Logger aussi dans les logs applicatifs
        log_msg = f"AUDIT: {action} {entity_type}"
        if entity_id:
            log_msg += f" #{entity_id}"
        log_msg += f" by {user}"

        if level == "ERROR":
            logger.error(log_msg)
        elif level == "WARNING":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    except Exception as e:
        # Ne jamais faire crasher l'app à cause du logging !
        logger.error(f"Failed to write audit log: {e}")


# 🎯 Fonctions helper pour actions courantes


def audit_book_created(book_id: int, title: str, user: str = "system") -> None:
    """Audite la création d'un livre."""
    log_audit(
        AuditAction.CREATE,
        AuditEntityType.BOOK,
        entity_id=book_id,
        user=user,
        details={"title": title},
    )


def audit_book_updated(book_id: int, changes: dict, user: str = "system") -> None:
    """Audite la modification d'un livre."""
    log_audit(
        AuditAction.UPDATE,
        AuditEntityType.BOOK,
        entity_id=book_id,
        user=user,
        details={"changes": changes},
    )


def audit_book_deleted(book_id: int, title: str, user: str = "system") -> None:
    """Audite la suppression d'un livre."""
    log_audit(
        AuditAction.DELETE,
        AuditEntityType.BOOK,
        entity_id=book_id,
        user=user,
        details={"title": title},
        level="WARNING",
    )


def audit_import(count: int, source: str, user: str = "system") -> None:
    """Audite un import de livres."""
    log_audit(
        AuditAction.IMPORT,
        AuditEntityType.BOOK,
        user=user,
        details={"count": count, "source": source},
    )


def audit_export(count: int, format: str, user: str = "system") -> None:
    """Audite un export de données."""
    log_audit(
        AuditAction.EXPORT,
        AuditEntityType.BOOK,
        user=user,
        details={"count": count, "format": format},
    )


# ===== MEMBRES =====


def audit_member_created(member_id: int, name: str, user: str = "system") -> None:
    """Audite la création d'un membre."""
    log_audit(
        AuditAction.CREATE,
        AuditEntityType.MEMBER,
        entity_id=member_id,
        user=user,
        details={"name": name},
    )


def audit_member_updated(member_id: int, changes: dict, user: str = "system") -> None:
    """Audite la modification d'un membre."""
    log_audit(
        AuditAction.UPDATE,
        AuditEntityType.MEMBER,
        entity_id=member_id,
        user=user,
        details={"changes": changes},
    )


def audit_member_deleted(member_id: int, name: str, user: str = "system") -> None:
    """Audite la suppression d'un membre."""
    log_audit(
        AuditAction.DELETE,
        AuditEntityType.MEMBER,
        entity_id=member_id,
        user=user,
        details={"name": name},
        level="WARNING",
    )


# ===== EMPRUNTS =====


def audit_loan_created(
    loan_id: int,
    book_id: int,
    member_id: int,
    book_title: str,
    member_name: str,
    user: str = "system",
) -> None:
    """Audite la création d'un emprunt."""
    log_audit(
        AuditAction.LOAN,
        AuditEntityType.LOAN,
        entity_id=loan_id,
        user=user,
        details={
            "book_id": book_id,
            "book_title": book_title,
            "member_id": member_id,
            "member_name": member_name,
        },
    )


def audit_loan_returned(
    loan_id: int,
    book_id: int,
    member_id: int,
    book_title: str,
    member_name: str,
    user: str = "system",
) -> None:
    """Audite le retour d'un emprunt."""
    log_audit(
        AuditAction.RETURN,
        AuditEntityType.LOAN,
        entity_id=loan_id,
        user=user,
        details={
            "book_id": book_id,
            "book_title": book_title,
            "member_id": member_id,
            "member_name": member_name,
        },
    )


# ===== RECHERCHE (OPTIONNEL) =====


def audit_search(query: str, result_count: int, user: str = "system") -> None:
    """Audite une recherche (optionnel - analytics)."""
    log_audit(
        AuditAction.SEARCH,
        AuditEntityType.BOOK,  # Ou générique
        user=user,
        details={"query": query, "result_count": result_count},
    )
