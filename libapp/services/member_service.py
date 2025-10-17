"""
Service de gestion de la logique métier des Membres.

Ce module fournit les opérations de haut niveau (CRUD) pour les membres,
en encapsulant l'accès à la base de données et en assurant la validation
des règles métier, comme l'unicité du numéro de membre.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..persistence.models_sa import Member, MemberStatus
from ..persistence.unit_of_work import UnitOfWork

logger = logging.getLogger("library.services.member")


@dataclass
class MemberDTO:
    """
    Data Transfer Object pour un Membre.

    Représente les données d'un membre telles qu'elles transitent entre
    l'interface utilisateur et la couche de service.
    """

    id: int | None
    member_no: str
    first_name: str
    last_name: str
    email: str = ""
    phone: str = ""
    status: str = "apprenti"
    is_active: bool = True


class MemberService:
    """Service gérant la logique métier des membres (CRUD)."""

    def __init__(self, uow_factory=lambda: UnitOfWork()):
        """Initialise le service avec une factory d'unités de travail."""
        self.uow_factory = uow_factory

    def list(self) -> list[Member]:
        """Retourne la liste de tous les membres présents en base."""
        with self.uow_factory() as uow:
            return uow.members.list()

    def _ensure_unique_member_no(
        self, uow: UnitOfWork, member_no: str, exclude_id: int | None = None
    ):
        """
        Vérifie que le numéro de membre est unique.

        Args:
            uow (UnitOfWork): L'unité de travail contenant la session.
            member_no (str): Le numéro de membre à vérifier.
            exclude_id (int, optional): L'ID du membre à exclure de la
                                        vérification (utile lors d'une mise à jour).

        Raises:
            ValueError: Si le numéro est vide ou déjà utilisé par un autre membre.
        """
        member_no = (member_no or "").strip()
        if not member_no:
            raise ValueError("Numéro de membre requis")

        query = uow.session.query(Member.id).filter(Member.member_no == member_no)
        if exclude_id is not None:
            query = query.filter(Member.id != exclude_id)

        if query.first():
            raise ValueError(f"Le numéro de membre '{member_no}' existe déjà.")

    def create(self, dto: MemberDTO) -> Member:
        """Crée un nouveau membre en validant l'unicité du numéro."""
        with self.uow_factory() as uow:
            self._ensure_unique_member_no(uow, dto.member_no)
            m = Member(
                member_no=dto.member_no.strip(),
                first_name=dto.first_name.strip(),
                last_name=dto.last_name.strip(),
                email=(dto.email or "").strip(),
                phone=(dto.phone or "").strip(),
                status=MemberStatus(dto.status),
                is_active=bool(dto.is_active),
            )
            uow.members.add(m)
            uow.commit()
            logger.info("Création membre: %s (%s %s)", m.member_no, m.first_name, m.last_name)
            return m

    def update(self, member_id: int, dto: MemberDTO) -> Member:
        """Met à jour un membre existant en validant l'unicité du numéro."""
        with self.uow_factory() as uow:
            m = uow.members.get(member_id)
            if not m:
                raise ValueError("Membre introuvable")

            self._ensure_unique_member_no(uow, dto.member_no, exclude_id=member_id)
            m.member_no = dto.member_no.strip()
            m.first_name = dto.first_name.strip()
            m.last_name = dto.last_name.strip()
            m.email = (dto.email or "").strip()
            m.phone = (dto.phone or "").strip()
            m.status = MemberStatus(dto.status)
            m.is_active = bool(dto.is_active)
            uow.commit()
            logger.info("MAJ membre id=%s: %s", member_id, m.member_no)
            return m

    def delete(self, member_id: int) -> None:
        """Supprime un membre par son identifiant."""
        with self.uow_factory() as uow:
            m = uow.members.get(member_id)
            if not m:
                return

            # Vérifier s'il y a des prêts en cours (règle métier)
            if uow.loans.list_open_by_member(member_id):
                raise ValueError("Impossible de supprimer un membre avec des prêts en cours.")

            uow.members.delete(m)
            uow.commit()
            logger.info("Suppression membre id=%s", member_id)
