from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_COMPUTED_FIELDS = frozenset({'paid_amount', 'remaining_amount'})

class InstallmentInstallment(models.Model):
    _name = 'installment.installment'
    _description = 'Customer Installment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', readonly=True, copy=False, default='New')
    reference = fields.Char(string='Reference')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('paid', 'Paid')
    ], string='Status', default='draft', required=True, tracking=True)

    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True,
                                 domain="[('type', 'in', ('sale', 'general'))]")
    account_id = fields.Many2one('account.account', string='Account', required=True,
                                 domain="[('account_type', 'in', ('asset_receivable', 'asset_cash'))]")

    analytic_distribution = fields.Json(string='Analytic Distribution', company_dependent=True)

    amount = fields.Float(string='Amount', required=True)
    notes = fields.Text(string='Notes')

    invoice_id = fields.Many2one('account.move', string='Related Invoice', readonly=True)
    payment_ids = fields.One2many('account.payment', 'installment_id', string='Payments')

    paid_amount = fields.Float(string='Paid Amount', compute='_compute_amounts', store=True)
    remaining_amount = fields.Float(string='Remaining Amount', compute='_compute_amounts', store=True)
    invoice_journal_id = fields.Many2one('account.journal', string='Invoice Journal',
                                         required=True, domain="[('type', '=', 'sale')]",
                                         default=lambda self: self.env['account.journal'].search(
                                             [('type', '=', 'sale')], limit=1))

    payment_journal_id = fields.Many2one('account.journal', string='Payment Journal',
                                         required=True, domain="[('type', 'in', ('bank', 'cash'))]",
                                         default=lambda self: self.env['account.journal'].search(
                                             [('type', 'in', ('bank', 'cash'))], limit=1))


    @api.constrains('amount')
    def _check_amount_positive(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("The installment amount must be strictly positive."))

    @api.depends('payment_ids.amount', 'payment_ids.state', 'amount')
    def _compute_amounts(self):
        for record in self:
            valid_payments = record.payment_ids.filtered(lambda p: p.state not in ('draft', 'canceled'))
            record.paid_amount = sum(valid_payments.mapped('amount'))
            record.remaining_amount = record.amount - record.paid_amount

    def write(self, vals):
        if self._context.get('bypass_draft_check'):
            return super().write(vals)

        check_fields = set(vals.keys()) - _COMPUTED_FIELDS - {'state'}
        if check_fields:
            for record in self:
                if record.state != 'draft':
                    raise ValidationError(_("You can only edit installments in the 'Draft' state"))
        return super().write(vals)

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_("You can only delete installments in the 'Draft' state."))
        return super().unlink()

    def action_open(self):
        for record in self.filtered(lambda r: r.state == 'draft'):
            new_name = (
                self.env['ir.sequence'].next_by_code('installment.installment') or 'New'
            )

            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': record.customer_id.id,
                'invoice_date': record.date,
                'journal_id': record.invoice_journal_id.id,
                'invoice_line_ids': [(0, 0, {
                    'name': _("Installment: %s") % new_name,
                    'account_id': record.account_id.id,
                    'quantity': 1.0,
                    'price_unit': record.amount,
                    'analytic_distribution': record.analytic_distribution,
                })],
            }
            record.with_context(bypass_draft_check=True).write({
                'name': new_name,
                'invoice_id': self.env['account.move'].create(invoice_vals).id,
                'state': 'open'
            })
    def action_settle(self):
        for record in self:
            if record.state != 'open':
                raise UserError(_("Only 'Open' installments can be settled."))

            if not record.invoice_id:
                raise UserError(_("No related invoice found for this installment."))

            if record.invoice_id.state == 'draft':
                record.invoice_id.action_post()

            if record.remaining_amount <= 0:
                record.with_context(bypass_draft_check=True).write({'state': 'paid'})
                continue

            available_lines = record.payment_journal_id._get_available_payment_method_lines('inbound')
            if not available_lines:
                raise ValidationError(
                    _("The journal '%s' has no inbound payment methods.") % record.payment_journal_id.name)

            payment = self.env['account.payment'].create({
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': record.customer_id.id,
                'amount': record.remaining_amount,
                'journal_id': record.payment_journal_id.id,
                'payment_method_line_id': available_lines[0].id,
                'memo': _("Settlement for %s") % record.name,
                'installment_id': record.id
            })
            payment.action_post()
            lines_to_reconcile = (payment.move_id.line_ids + record.invoice_id.line_ids).filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )
            if lines_to_reconcile:
                lines_to_reconcile.reconcile()

            record.with_context(bypass_draft_check=True).write({'state': 'paid'})

    def action_view_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
            'target': 'current',
        }