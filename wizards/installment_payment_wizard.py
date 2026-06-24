from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InstallmentPaymentWizard(models.TransientModel):
    _name = 'installment.payment.wizard'
    _description = 'Installment Payment Wizard'

    installment_id = fields.Many2one('installment.installment', string='Installment', required=True)
    journal_id = fields.Many2one('account.journal', string='Payment Method/Journal', required=True)
    amount_to_pay = fields.Float(string='Amount to Pay', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super(InstallmentPaymentWizard, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            installment = self.env['installment.installment'].browse(active_id)
            res.update({
                'installment_id': installment.id,
                'amount_to_pay': installment.remaining_amount,
                'journal_id': installment.payment_journal_id.id,
            })
        return res

    def action_confirm_payment(self):
        self.ensure_one()
        if self.amount_to_pay <= 0:
            raise ValidationError("Payment amount must be greater than zero.")
        if self.amount_to_pay > self.installment_id.remaining_amount:
            raise ValidationError(
                "You cannot pay more than the remaining installment amount (%s)." % self.installment_id.remaining_amount
            )

        if self.installment_id.invoice_id and self.installment_id.invoice_id.state == 'draft':
            self.installment_id.invoice_id.action_post()

        available_lines = self.journal_id._get_available_payment_method_lines('inbound')
        if not available_lines:
            raise ValidationError(
                "The selected journal '%s' has no inbound payment methods configured." % self.journal_id.name
            )

        # 2. Create and post the core Odoo payment
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.installment_id.customer_id.id,
            'amount': self.amount_to_pay,
            'journal_id': self.journal_id.id,
            'payment_method_line_id': available_lines[0].id,
            'memo': f"Payment for Installment: {self.installment_id.name}",
            'installment_id': self.installment_id.id,
        })
        payment.action_post()

    

        return {'type': 'ir.actions.act_window_close'}
