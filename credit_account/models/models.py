# -*- coding: utf-8 -*-

from odoo import models, fields, api

# class credit_account(models.Model):
#     _name = 'credit_account.credit_account'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100

class PaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    #TODO: Add payment terms here
