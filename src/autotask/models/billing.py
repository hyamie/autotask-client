"""Invoice and billing entity models."""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from autotask.models.base import AutotaskModel


class Invoice(AutotaskModel):
    _entity_type: ClassVar[str] = "Invoices"

    invoiceNumber: str | None = None
    invoiceDateTime: datetime | None = None
    invoiceStatus: int | None = None
    invoiceTotal: float | None = None
    companyID: int | None = None
    fromDate: datetime | None = None
    toDate: datetime | None = None
    dueDate: datetime | None = None
    paidDate: datetime | None = None
    comments: str | None = None
    orderNumber: str | None = None
    paymentTerm: int | None = None
    taxGroup: int | None = None
    totalTaxValue: float | None = None
    isVoided: bool | None = None
    voidedByResourceID: int | None = None
    voidedDate: datetime | None = None
    batchID: int | None = None
    creatorResourceID: int | None = None
    createDateTime: datetime | None = None
    invoiceEditorTemplateID: int | None = None
    webServiceDate: datetime | None = None


class BillingItem(AutotaskModel):
    _entity_type: ClassVar[str] = "BillingItems"

    billingItemType: int | None = None
    subType: int | None = None
    itemName: str | None = None
    description: str | None = None
    itemDate: datetime | None = None
    quantity: float | None = None
    rate: float | None = None
    extendedPrice: float | None = None
    totalAmount: float | None = None
    ourCost: float | None = None
    taxDollars: float | None = None
    nonBillable: int | None = None
    companyID: int | None = None
    contractID: int | None = None
    invoiceID: int | None = None
    projectID: int | None = None
    taskID: int | None = None
    ticketID: int | None = None
    timeEntryID: int | None = None
    billingCodeID: int | None = None
    configurationItemID: int | None = None
    contractChargeID: int | None = None
    contractServiceID: int | None = None
    contractServiceBundleID: int | None = None
    contractBlockID: int | None = None
    milestoneID: int | None = None
    expenseItemID: int | None = None
    ticketChargeID: int | None = None
    projectChargeID: int | None = None
    roleID: int | None = None
    serviceID: int | None = None
    serviceBundleID: int | None = None
    vendorID: int | None = None
    accountManagerWhenApprovedID: int | None = None
    itemApproverID: int | None = None
    lineItemFullDescription: str | None = None
    lineItemGroupDescription: str | None = None
    purchaseOrderNumber: str | None = None
    postedDate: datetime | None = None
    postedOnTime: datetime | None = None
    sortOrderID: int | None = None
    webServiceDate: datetime | None = None


class BillingCode(AutotaskModel):
    _entity_type: ClassVar[str] = "BillingCodes"

    name: str | None = None
    description: str | None = None
    billingCodeType: int | None = None
    useType: int | None = None
    isActive: bool | None = None
    unitCost: float | None = None
    unitPrice: float | None = None
    externalNumber: str | None = None
    department: int | None = None
    generalLedgerAccount: int | None = None
    isExcludedFromNewContracts: bool | None = None
    markupRate: float | None = None
    taxCategoryID: int | None = None
    afterHoursWorkType: int | None = None
