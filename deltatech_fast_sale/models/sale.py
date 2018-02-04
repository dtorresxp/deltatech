# -*- coding: utf-8 -*-
# ©  2015-2018 Deltatech
#              Dorin Hongu <dhongu(@)gmail(.)com
# See README.rst file on addons root folder for license details



from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo import models, fields, api, _
from odoo.tools.translate import _
from odoo import SUPERUSER_ID, api
import odoo.addons.decimal_precision as dp


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_button_confirm_to_invoice(self):
        if self.state == 'draft':
            self.action_confirm()  # confirma comanda

        for picking in self.picking_ids:
            if picking.state not in ['done']:
                picking.action_assign()  # verifica disponibilitate
                if not all(move.state == 'assigned' for move in picking.move_lines):
                    raise Warning(_('Not all products are available.'))

                for move_line in picking.move_lines:
                    if move_line.product_uom_qty > 0 and move_line.quantity_done == 0 :
                        move_line.write({'quantity_done': move_line.product_uom_qty})
                    else:
                        move_line.unlink()
                picking.do_transfer()

        action_obj = self.env.ref('sale.action_view_sale_advance_payment_inv')
        action = action_obj.read()[0]

        return action

