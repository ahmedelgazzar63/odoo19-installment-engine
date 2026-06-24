from odoo import models, fields, _

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    installment_id = fields.Many2one('installment.installment', string='Originating Installment', ondelete='set null')

    def action_post(self):
        res = super().action_post()
        for payment in self:
            installment = payment.installment_id
            if not installment or installment.state != 'open':
                continue

            installment._compute_amounts()
            if installment.remaining_amount <= 0:
                installment.with_context(bypass_draft_check=True).write({'state': 'paid'})
        return res
