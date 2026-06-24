# Odoo Installment & Payment Management Module

A custom Odoo module designed to manage customer installments with integrated automated invoicing, automated/wizard-driven payments, and automated accounting reconciliation.

## 🚀 Technical Features & Core Logic (From Source Code)

### 1. Installment Core Business Logic (`installment.installment`)
- **State Control & Security:** Restricts any editing (`write`) or deletion (`unlink`) of installment records unless they are in the `Draft` state.
- **Automated Invoicing (`action_open`):** Automatically creates a customer invoice (`account.move`) with the installment's amount, financial account, and analytic distribution upon opening.
- **Full Settlement (`action_settle`):** Posts the related invoice, creates a full inbound payment (`account.payment`), and executes an immediate reconciliation (`.reconcile()`) between the invoice and payment lines under the `asset_receivable` account to mark the invoice as paid.
- **Dynamic Computations:** Computes `paid_amount` and `remaining_amount` in real-time based on associated non-draft and non-canceled payments.

### 2. Flexible Payment Wizard (`installment.payment.wizard`)
- **Data Pre-population (`default_get`):** Automatically captures the active installment context to pre-fill the wizard fields with the correct installment reference, remaining balance, and default payment journal.
- **Strict Payment Validations:** Validates inputs before processing to ensure the payment amount is strictly greater than zero and does not exceed the installment's remaining balance.
- **Custom Payment Creation:** Generates and posts an optimized `account.payment` record for the exact customized amount entered by the user.

### 3. Native Odoo Payment Hook (`account.payment` Inheritance)
- **Post-Processing Hook (`action_post`):** Inherits Odoo's native payment posting method. After a standard payment is posted, it triggers a re-computation of the installment's financial amounts (`_compute_amounts()`).
- **Automated State Transition:** Automatically updates the linked installment's status to `Paid` the exact moment the remaining balance reaches zero.

---

## 📁 Applied Odoo Concepts
- **Models Used:** `models.Model` (Core), `models.TransientModel` (Wizard), and Model Inheritance (`_inherit` on `account.payment`).
- **ORM Methods & Decorators:** `@api.depends`, `@api.constrains`, `default_get`, `with_context`, and `.filtered()`.
- **Accounting Framework:** Integration with `account.move` (Invoices), `account.payment` (Payments), and `.reconcile()` (Account Matching).

---

## 🧑‍💻 Author
**Ahmed Elgazzar** - *Junior Odoo Developer*
