"""Contract entity model and child entities."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from autotask.models.base import AutotaskModel


class Contract(AutotaskModel):
    _entity_type: ClassVar[str] = "Contracts"

    companyID: int | None = None
    contractName: str | None = None
    contractNumber: str | None = None
    contractType: int | None = None
    contractCategory: int | None = None
    contractPeriodType: int | None = None
    status: int | None = None
    startDate: datetime | None = None
    endDate: datetime | None = None
    description: str | None = None
    estimatedCost: float | None = None
    estimatedHours: float | None = None
    estimatedRevenue: float | None = None
    setupFee: float | None = None
    setupFeeBillingCodeID: int | None = None
    overageBillingRate: float | None = None
    billingPreference: int | None = None
    contactID: int | None = None
    contactName: str | None = None
    billToCompanyID: int | None = None
    billToCompanyContactID: int | None = None
    opportunityID: int | None = None
    purchaseOrderNumber: str | None = None
    renewedContractID: int | None = None
    exclusionContractID: int | None = None
    contractExclusionSetID: int | None = None
    isDefaultContract: bool | None = None
    isCompliant: bool | None = None
    serviceLevelAgreementID: int | None = None
    timeReportingRequiresStartAndStopTimes: int | None = None
    organizationalLevelAssociationID: int | None = None
    lastModifiedDateTime: datetime | None = None


class ContractService(AutotaskModel):
    _entity_type: ClassVar[str] = "ContractServices"

    contractID: int | None = None
    serviceID: int | None = None
    unitPrice: float | None = None
    unitCost: float | None = None
    internalDescription: str | None = None
    invoiceDescription: str | None = None
    quoteItemID: int | None = None


class ContractServiceBundle(AutotaskModel):
    _entity_type: ClassVar[str] = "ContractServiceBundles"

    contractID: int | None = None
    serviceBundleID: int | None = None
    adjustedPrice: float | None = None
    unitPrice: float | None = None
    internalDescription: str | None = None
    invoiceDescription: str | None = None
    quoteItemID: int | None = None


class ContractCharge(AutotaskModel):
    _entity_type: ClassVar[str] = "ContractCharges"

    contractID: int | None = None
    name: str | None = None
    description: str | None = None
    chargeType: int | None = None
    datePurchased: datetime | None = None
    unitQuantity: float | None = None
    unitPrice: float | None = None
    unitCost: float | None = None
    billableAmount: float | None = None
    extendedCost: float | None = None
    billingCodeID: int | None = None
    productID: int | None = None
    contractServiceID: int | None = None
    contractServiceBundleID: int | None = None
    isBillableToCompany: bool | None = None
    isBilled: bool | None = None
    status: int | None = None
    notes: str | None = None
    purchaseOrderNumber: str | None = None
    internalPurchaseOrderNumber: str | None = None
    creatorResourceID: int | None = None
    createDate: datetime | None = None
    statusLastModifiedBy: int | None = None
    statusLastModifiedDate: datetime | None = None


class ContractBillingRule(AutotaskModel):
    _entity_type: ClassVar[str] = "ContractBillingRules"

    contractID: int | None = None
    productID: int | None = None
    isActive: bool | None = None
    startDate: datetime | None = None
    endDate: datetime | None = None
    createChargesAsBillable: bool | None = None
    determineUnits: int | None = None
    executionMethod: int | None = None
    minimumUnits: int | None = None
    maximumUnits: int | None = None
    includeItemsInChargeDescription: bool | None = None
    isDailyProrationEnabled: bool | None = None
    dailyProratedCost: float | None = None
    dailyProratedPrice: float | None = None
    invoiceDescription: str | None = None
