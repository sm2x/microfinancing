# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo import tools, _

from odoo.exceptions import ValidationError, UserError

#TODO: VALIDATION ON DRAFT
class GroupEvaluation(models.Model):
    _name = 'credit.group.evaluation'

    name = fields.Char(related='group_id.name')
    registration_ids = fields.One2many('event.registration','evaluation_id','Loan History')
    indicator_ids = fields.One2many('credit.group.evaluation.form', 'evaluation_id')
    group_id = fields.Many2one('credit.loan.group', 'Group')
    area_id = fields.Many2one('res.area',related='group_id.area_id')
    branch_id = fields.Many2one('res.branch', related='area_id.branch_id')
    application_ids = fields.One2many('crm.lead', related='group_id.application_ids')
    is_complete = fields.Boolean(default=False, compute='set_complete')
    evaluation_date = fields.Datetime(default=fields.Datetime.now())
    product_id = fields.Many2one('product.template', related='group_id.product_id', string='Loan Type')
    attachments = fields.Many2many('ir.attachment', string='Prerequisites')
    total_score = fields.Integer('Total', compute='_get_mean_score')
    decision = fields.Selection([('approve','Approved'),
                                 ('reject','Rejected'),
                                 ('evaluate','For further evaluation')], 'Quality Strategic Decision')
    crecoms = fields.One2many('credit.group.evaluation.crecom','evaluation_id')
    status = fields.Selection([('draft', 'Draft'),
                               ('ongoing', 'Ongoing'),
                               ('done', 'Done'),
                               ('cancel', 'Cancelled')], default='draft')
    def set_complete(self):
        try:
            for rec in self:
                self.is_complete = (len(rec.application_ids) == len(rec.registration_ids)) * (self.total_score>=4)
        except Exception as e:
            raise UserError(_("ERROR: 'set_complete' "+str(e)))

    def _get_mean_score(self):
        for rec in self:
            try:
                rec.total_score = sum([indicator.weighted_score for indicator in rec.indicator_ids])
            except ZeroDivisionError as zde:
                raise ValidationError(_("ZeroDivisionError: '_get_mean_score' "+str(zde)))
            except Exception as e:
                raise UserError(_("ERROR: '_get_mean_score' "+str(e)))
    @api.one
    def draft_form(self):
        self.status = 'draft'

    @api.one
    def confirm_form(self):
        self.status = 'ongoing'

    @api.one
    def cancel_form(self):
        self.status = 'cancel'

    @api.one
    def done_form(self):
        if self.is_complete:
            self.status = 'done'
            #TODO: Generate Collection/Amortization


        else:
            raise ValidationError(_('Evaluation must be completed first!'))

    @api.onchange('is_complete')
    def set_done(self):
        if self.is_complete:
            self.status = 'done'

    @api.model
    def create(self, values):
        ev = super(GroupEvaluation, self).create(values)
        form = self.env['credit.group.evaluation.form'].search([('evaluation_id','=',ev.id)],limit=1)
        if not form:
            try:
                for i in self.env['credit.group.evaluation.csi'].search([]):
                    self.env['credit.group.evaluation.form'].create({
                        'evaluation_id': ev.id,
                        'cs_indicator_id':i.id
                    })
                ev['status'] = 'ongoing'
            except Exception as e:
                raise UserError(_('ERROR 3 '+str(e)))
        return ev

class LoanApplicationRemarks(models.Model):
    _name = 'credit.loan.application.remarks'

    name = fields.Char()
    content = fields.Text()

class LoanApplication(models.Model):
    _inherit = 'crm.lead'

    status = fields.Selection(string='Status', selection_add=[('confirm','Confirmed'),('evaluate', 'Evaluation')], required=True, track_visibility='onchange')
    registration_ids = fields.One2many('event.registration','application_id')
    performance_id = fields.Many2one('credit.loan.application.remarks','Performance')

class LoanGroup(models.Model):
    _inherit = 'credit.loan.group'

    status = fields.Selection(selection_add=[('evaluate', 'Evaluation')], required=True, track_visibility='onchange')
    is_approved = fields.Boolean(default=False, compute='set_approved', string='State')
    # is_complete = fields.Boolean(default=False, compute='set_approved')
    evaluation_ids = fields.One2many('credit.group.evaluation','group_id', 'Evaluations')

    @api.one
    def evaluate_group(self):
        if self.is_approved:
            try:

                me = self.env['event.event'].search(
                    [('event_type_id.name', '=', 'Membership Education'), ('state', '=', 'confirm')],
                    order='date_begin desc', limit=1)

                if not me:
                    raise UserError(_('Set Membership Education Event first!'))

                ev = self.evaluation_ids.search([('group_id','=',self.id)], order='evaluation_date desc', limit=1)
                if not ev:
                    ev = self.env['credit.group.evaluation'].create({
                            'group_id': self.id,
                        })
                for application_id in self.application_ids:
                    application = self.env['crm.lead'].search(
                        [('partner_id', '=', application_id.partner_id.id), ('group_id', '=', self.id), ('state', '=', True)])
                    self.env['event.registration'].create({
                        'event_id': me.id,
                        'evaluation_id': ev.id,
                        'application_id': application.id,
                        'partner_id': application_id.partner_id.id,
                    })
                    try:
                        self.env['crm.lead'].search([('id', '=', application.id)]).stage_id = \
                        self.env['crm.stage'].search([('name', '=', 'Qualified')])
                    except ValueError as ve:
                        raise UserError(_(str(ve) + '\nConfirm group first!'))
                    except Exception as e:
                        raise UserError(_("ERROR: '(evaluate_group)'"+str(e)))
                    application.write({
                        'status':'evaluate'
                    })
            except Exception as e:
                raise UserError(_("ERROR 'evaluate_group' "+str(e)))
            self.status = 'evaluate'
        else:
            raise ValidationError(_('All members\'s application must be approved'))


    @api.depends('application_ids')
    def set_approved(self):
        for rec in self:
            rec.is_approved = (len(rec.application_ids) == sum([_bool.investigation_status for _bool in rec.application_ids]))
            # self.is_complete = (len(rec.members) == sum([((int(self.env['credit.loan.application'].search([('partner_id','=',member.id),('group_id','=',rec.id),('state','=',True)], order='application_date desc', limit=1).partner_id.id) for member in members) for members in evaluation)for evaluation in self.evaluation_ids]))

class CrecomEvaluation(models.Model):
    _name = 'credit.group.evaluation.crecom'

    name = fields.Char()
    evaluation_id = fields.Many2one('credit.group.evaluation')
    is_passed = fields.Boolean(default=False)
    others = fields.Text()

class CriticalSuccessSubIndicators(models.Model):
    _name = 'credit.group.evaluation.cssi'

    name = fields.Char()
    indicator_id = fields.Many2one('credit.group.evaluation.csi')

class CriticalSuccessIndicators(models.Model):
    _name = 'credit.group.evaluation.csi'

    name = fields.Char()
    form_id = fields.Many2one('credit.group.evaluation.form')
    weight = fields.Float(digits=(0,2),string='Weight')
    subindicators = fields.One2many('credit.group.evaluation.cssi','indicator_id')

class GroupEvaluationForm(models.Model):
    _name = 'credit.group.evaluation.form'

    name = fields.Char(related='cs_indicator_id.name')
    weight = fields.Float(related='cs_indicator_id.weight')
    evaluation_id = fields.Many2one('credit.group.evaluation')
    cs_indicator_id = fields.Many2one('credit.group.evaluation.csi', 'Critical Success Indicators')
    subindicators = fields.One2many('credit.group.evaluation.cssi',related='cs_indicator_id.subindicators')
    rating = fields.Integer('Rating')
    weighted_score = fields.Float('Weighted Score', compute='_compute_score')
    proof = fields.Text('Proof of Evidence')

    @api.depends('rating', 'weight')
    def _compute_score(self):
        try:
            for rec in self:
                rec.weighted_score = rec.rating * rec.weight
        except Exception as e:
            raise ValidationError(_("ERROR: '_compute_score' "+str(e)))

class EventRegistration(models.Model):
    _inherit = 'event.registration'

    application_id = fields.Many2one('crm.lead','Application')
    evaluation_id = fields.Many2one('credit.group.evaluation','Evaluation')
    application = fields.Char(related='application_id.name')
    application_status = fields.Selection(related='application_id.status')
