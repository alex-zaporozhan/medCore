import i18n from "@/i18n";

export function moneyYesNo(value: boolean): string {
  return i18n.t(value ? "yes" : "no", { ns: "money" });
}

export function moneyCashboxTypeLabel(type: string): string {
  switch (type) {
    case "cash":
    case "card":
    case "bank_account":
    case "other":
      return i18n.t(`cashboxTypes.${type}`, { ns: "money" });
    default:
      return type;
  }
}

export function moneyDiscountTypeLabel(type: string): string {
  switch (type) {
    case "first_visit":
    case "service":
    case "doctor":
    case "period":
      return i18n.t(`discountTypes.${type}`, { ns: "money" });
    default:
      return type;
  }
}

export function moneyFinanceTxTypeLabel(type: string): string {
  switch (type) {
    case "income":
    case "expense":
    case "transfer":
      return i18n.t(`finance.txType.${type}`, { ns: "money" });
    default:
      return type;
  }
}

export function moneySalaryTxTypeLabel(type: string): string {
  switch (type) {
    case "accrual":
    case "adjustment":
    case "payout":
      return i18n.t(`finance.salaryTxType.${type}`, { ns: "money" });
    default:
      return type;
  }
}

export function moneyInventoryTxTypeLabel(type: string): string {
  switch (type) {
    case "incoming":
    case "outgoing":
    case "adjustment":
      return i18n.t(`finance.inventoryTxType.${type}`, { ns: "money" });
    default:
      return type;
  }
}

export function moneyFinanceTxSourceLabel(source: string): string {
  switch (source) {
    case "cash":
    case "acquiring":
    case "package":
    case "deposit":
    case "discount":
    case "other":
      return i18n.t(`finance.txSource.${source}`, { ns: "money" });
    default:
      return source;
  }
}

export function moneyMovementKindLabel(kind: string): string {
  switch (kind) {
    case "goods_in":
    case "goods_out":
    case "goods_transfer":
      return i18n.t(`movementKinds.${kind}`, { ns: "money" });
    default:
      return kind;
  }
}

export function moneyGatewayLabel(gateway: string): string {
  switch (gateway) {
    case "yookassa":
    case "tinkoff":
    case "sber":
    case "robokassa":
    case "stripe":
    case "paypal":
    case "custom":
      return i18n.t(`gateway.${gateway}`, { ns: "money" });
    default:
      return gateway;
  }
}

export function moneyPrepaymentScopeLabel(scope: string): string {
  switch (scope) {
    case "service":
    case "doctor":
    case "doctor_service":
      return i18n.t(`prepayment.scope.${scope}`, { ns: "money" });
    default:
      return scope;
  }
}

export function moneyPrepaymentModeLabel(mode: string): string {
  switch (mode) {
    case "none":
    case "partial":
    case "full":
      return i18n.t(`prepayment.mode.${mode}`, { ns: "money" });
    default:
      return mode;
  }
}

export function moneyPrepaymentAmountTypeLabel(amountType: string): string {
  switch (amountType) {
    case "fixed":
    case "percent":
      return i18n.t(`prepayment.amountType.${amountType}`, { ns: "money" });
    default:
      return amountType;
  }
}

export function moneyLoyaltyPackageKindLabel(kind: string): string {
  switch (kind) {
    case "COUNT_BASED":
    case "visits":
    case "BALANCE_BASED":
    case "balance":
      return i18n.t(`loyalty.packageKind.${kind}`, { ns: "money" });
    default:
      return kind;
  }
}

export function moneyWalletTxTypeLabel(type: string): string {
  switch (type) {
    case "earn":
    case "spend":
    case "expire":
    case "adjustment":
      return i18n.t(`loyalty.walletTxType.${type}`, { ns: "money" });
    default:
      return type;
  }
}

export function moneyPassStatusLabel(status: string): string {
  switch (status) {
    case "active":
    case "expired":
    case "used_up":
    case "cancelled":
      return i18n.t(`loyalty.passStatus.${status}`, { ns: "money" });
    default:
      return status;
  }
}
