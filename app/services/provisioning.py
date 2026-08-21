"""Provisioning planning without card mutation."""

from app.adapters.sim_cards import SIMCardAdapter
from app.services.profiles import ProfileVaultService
from app.models import (
    CardComparisonRequest,
    CardComparisonResult,
    ProvisioningDraft,
    ProvisioningPreview,
    ProvisioningStep,
)


class ProvisioningPreviewService:
    """Create a redacted dry-run plan; this service has no hardware adapter."""

    def create_preview(self, draft: ProvisioningDraft) -> ProvisioningPreview:
        steps = [
            ProvisioningStep(
                order=1,
                target="MF/EF.ICCID",
                action="Kartenkennung vorbereiten",
                fields=["ICCID"],
                risk="Identität der physischen Karte",
            ),
            ProvisioningStep(
                order=2,
                target="ADF.USIM/EF.IMSI und EF.ACC",
                action="Teilnehmerkennung vorbereiten",
                fields=["IMSI", "ACC"],
                risk="Netzregistrierung des Teilnehmers",
            ),
            ProvisioningStep(
                order=3,
                target="Authentisierungsparameter",
                action="Schlüsselmaterial vorbereiten",
                fields=["Ki", "OPc"],
                risk="Hochsensibles Schlüsselmaterial",
            ),
            ProvisioningStep(
                order=4,
                target="Administrativer Zugang",
                action="ADM-Zugang vorbereiten",
                fields=["ADM"],
                risk="Schreibschutz der Karte",
            ),
        ]
        if draft.msisdn:
            steps.insert(
                2,
                ProvisioningStep(
                    order=3,
                    target="DF.TELECOM/EF.MSISDN",
                    action="Rufnummer vorbereiten",
                    fields=["MSISDN"],
                    risk="Teilnehmer-Rufnummer",
                ),
            )
            for index, step in enumerate(steps, start=1):
                step.order = index
        if draft.impi or draft.impu or draft.ims_domain or draft.ist:
            steps.append(ProvisioningStep(
                order=len(steps) + 1,
                target="ADF.ISIM",
                action="IMS-Profildaten vormerken",
                fields=[field for field, value in (("IMPI", draft.impi), ("IMPU", draft.impu), ("DOMAIN", draft.ims_domain), ("IST", draft.ist)) if value],
                risk="Nur verschlüsselte Profilspeicherung; kein SIM-Schreibpfad",
            ))
        if draft.routing_indicator or draft.protection_scheme is not None or draft.hn_public_key_id is not None or draft.hn_public_key:
            steps.append(ProvisioningStep(
                order=len(steps) + 1,
                target="ADF.USIM/5GS",
                action="5GS-/SUCI-Profildaten vormerken",
                fields=[field for field, value in (("Routing Indicator", draft.routing_indicator), ("Protection Scheme", draft.protection_scheme), ("HN Public Key ID", draft.hn_public_key_id), ("HN Public Key", draft.hn_public_key)) if value is not None and value != ""],
                risk="Nur verschlüsselte Profilspeicherung; kein SIM-Schreibpfad",
            ))

        return ProvisioningPreview(
            iccid=draft.iccid,
            imsi=draft.imsi,
            msisdn=draft.msisdn,
            acc=draft.acc.upper(),
            ki_configured=bool(draft.ki.get_secret_value()),
            opc_configured=bool(draft.opc.get_secret_value()),
            adm_configured=bool(draft.adm.get_secret_value()),
            steps=steps,
            warnings=[
                "Dry-Run: Es wurden keine Daten auf eine SIM geschrieben.",
                "Ki, OPc und ADM werden weder zurückgegeben noch gespeichert.",
                "Vor einem späteren Schreibvorgang sind Kartenabgleich und Bestätigung erforderlich.",
            ],
        )


class CardComparisonService:
    """Compare a draft to a card through the existing read-only adapter."""

    def __init__(self, adapter: SIMCardAdapter) -> None:
        self._adapter = adapter

    def compare(self, request: CardComparisonRequest) -> CardComparisonResult:
        current = self._adapter.read_identity(request.reader_index)
        iccid_matches = current.iccid == request.target_iccid
        imsi_matches = current.imsi == request.target_imsi
        warnings: list[str] = []
        if not iccid_matches:
            warnings.append("Die Ziel-ICCID weicht von der eingelegten Karte ab.")
        if not imsi_matches:
            warnings.append("Die Ziel-IMSI weicht von der eingelegten Karte ab.")
        if iccid_matches and imsi_matches:
            warnings.append("ICCID und IMSI entsprechen bereits dem Entwurf.")
        suci_compared = request.target_protection_scheme is not None
        suci_values = {
            "routing_indicator_matches": None, "protection_scheme_matches": None,
            "hn_public_key_id_matches": None, "hn_public_key_matches": None, "suci_matches": None,
        }
        if suci_compared and current.suci_readable:
            suci_values = {
                "routing_indicator_matches": current.routing_indicator == request.target_routing_indicator,
                "protection_scheme_matches": current.protection_scheme == request.target_protection_scheme,
                "hn_public_key_id_matches": current.hn_public_key_id == request.target_hn_public_key_id,
                "hn_public_key_matches": (current.hn_public_key or "").upper() == (request.target_hn_public_key or "").upper(),
                "suci_matches": False,
            }
            suci_values["suci_matches"] = all(value for key, value in suci_values.items() if key != "suci_matches") and current.suci_service_124_active is True and current.suci_service_125_active is False
            if not suci_values["suci_matches"]:
                warnings.append("Die SUCI-Konfiguration der Karte weicht vom Tresorprofil ab.")
        elif suci_compared:
            warnings.append("Die SUCI-Konfiguration konnte auf dieser Karte nicht gelesen werden.")
        warnings.append("Der Kartenabgleich hat keine Daten verändert.")

        return CardComparisonResult(
            reader_index=current.reader_index,
            card_type=current.card_type,
            atr=current.atr,
            current_iccid=current.iccid,
            current_imsi=current.imsi,
            target_iccid=request.target_iccid,
            target_imsi=request.target_imsi,
            iccid_matches=iccid_matches,
            imsi_matches=imsi_matches,
            suci_compared=suci_compared,
            suci_readable=current.suci_readable,
            current_routing_indicator=current.routing_indicator,
            current_protection_scheme=current.protection_scheme,
            current_hn_public_key_id=current.hn_public_key_id,
            suci_service_124_active=current.suci_service_124_active,
            suci_service_125_active=current.suci_service_125_active,
            **suci_values,
            warnings=warnings,
        )


class ProfileWriteService:
    """Write a pending standard-field change and commit it only after verification."""

    SUPPORTED_FIELDS = {"imsi", "msisdn", "acc", "ki", "opc", "impi", "impu", "ims_domain", "ist", "routing_indicator", "protection_scheme", "hn_public_key_id", "hn_public_key"}

    def __init__(self, adapter: SIMCardAdapter, vault: ProfileVaultService) -> None:
        self._adapter = adapter; self._vault = vault

    def execute(self, profile_id: int, reader_index: int = 0) -> tuple[int, list[str]]:
        summary = self._vault.get_change_summary(profile_id)
        if summary is None: raise KeyError(profile_id)
        changed = set(summary.changed_fields)
        unsupported = changed - self.SUPPORTED_FIELDS
        if unsupported: raise ValueError("unsupported_fields")
        draft = self._vault.get_change_draft(profile_id)
        base_args = (reader_index, draft.iccid, draft.imsi, draft.acc, draft.msisdn,
            draft.adm.get_secret_value(), sorted(changed), draft.ki.get_secret_value(), draft.opc.get_secret_value(),
            draft.impi, draft.impu, draft.ims_domain, draft.ist)
        fivegs_fields = {"routing_indicator", "protection_scheme", "hn_public_key_id", "hn_public_key"}
        if changed & fivegs_fields:
            verified = self._adapter.write_standard_fields(*base_args, draft.routing_indicator, draft.protection_scheme,
                draft.hn_public_key_id, draft.hn_public_key)
        else:
            verified = self._adapter.write_standard_fields(*base_args)
        if set(verified) != changed: raise ValueError("verification_failed")
        revision = self._vault.commit_change(profile_id, summary.base_revision)
        return revision, verified
