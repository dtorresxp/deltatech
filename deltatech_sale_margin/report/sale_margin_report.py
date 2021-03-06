# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008 Deltatech All Rights Reserved
#                    Dorin Hongu <dhongu(@)gmail(.)com       
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields,osv
from openerp import tools
import openerp.addons.decimal_precision as dp
from openerp import models, api, _


class sale_margin_report(models.Model):
    _name = "sale.margin.report"
    _description = "Sale Margin Report"
    _auto = False
    _order = 'date desc'
     

    _columns = {
        
        'date': fields.date('Date', readonly=True),
        'invoice_id': fields.many2one('account.invoice', 'Invoice', readonly=True),
        'categ_id': fields.many2one('product.category', 'Category', readonly=True), 
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure', readonly=True),
        'product_uom_qty': fields.float('Quantity', readonly=True),
        #'purchase_price': fields.float('Purchase price', readonly=True ),
        'sale_val': fields.float('Sale value', readonly=True, help="Sale value in company currency" ),
 
        'stock_val': fields.float("Stock value",  readonly=True, help="Stock value in company currency"),
        'profit_val': fields.float("Profit",   readonly=True, help="Profit obtained at invoicing in company currency"),
        'commission_computed': fields.float("Commission Computed",   readonly=True),
        'commission': fields.float("Commission"),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'commercial_partner_id': fields.many2one('res.partner', 'Commercial Partner', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesperson'),
        
        'company_id': fields.many2one('res.company','Company',readonly=True), 
        
        'period_id': fields.many2one('account.period', 'Period', readonly=True),
        'indicator_supplement': fields.float("Supplement Indicator",   readonly=True, digits=(12,2), group_operator='avg'),
        'indicator_profit': fields.float("Profit Indicator",   readonly=True, digits=(12,2), group_operator='avg'),
        
        'journal_id': fields.many2one('account.journal', 'Journal', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'currency_rate': fields.float('Currency Rate', readonly=True),
        
        'type': fields.selection([
            ('out_invoice','Customer Invoice'),
            ('in_invoice','Supplier Invoice'),
            ('out_refund','Customer Refund'),
            ('in_refund','Supplier Refund'),
            ],'Type', readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('proforma','Pro-forma'),
            ('proforma2','Pro-forma'),
            ('open','Open'),
            ('paid','Done'),
            ('cancel','Cancelled')
            ], 'Invoice Status', readonly=True),

    }
    

    def _select(self):
        select_str = """
            SELECT 
                id, date, invoice_id, categ_id, product_id, product_uom, product_uom_qty , 
                sale_val / cr.rate as sale_val, 
                stock_val  as stock_val, 
                (sale_val  / cr.rate - stock_val ) as profit_val, 
                
                CASE
                     WHEN (stock_val ) = 0
                      THEN 0
                      ELSE  100 * (sale_val  / cr.rate - stock_val ) / stock_val
                END  AS indicator_supplement,  
                
                CASE
                     WHEN (sale_val / cr.rate ) = 0
                      THEN 0
                      ELSE  100 * (sale_val  / cr.rate - stock_val ) / (sale_val / cr.rate ) 
                END  AS indicator_profit,               
 
                
                sub.rate * (sale_val  / cr.rate - stock_val ) as commission_computed,
                commission,  
                partner_id, commercial_partner_id, user_id, period_id,  company_id,
                type,  state ,  journal_id, 
                cr.rate as currency_rate,
                 sub.currency_id 
        """
        return select_str

    def _sub_select(self):
        select_str = """
                SELECT
                    min(l.id) as id,
                    s.date_invoice as date,               
                    l.invoice_id as invoice_id,                 
                    t.categ_id as categ_id,                    
                    l.product_id as product_id,
                    t.uom_id as product_uom,
                    

                    SUM(CASE
                     WHEN s.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                        THEN -(l.quantity / u.factor * u2.factor)
                        ELSE  (l.quantity / u.factor * u2.factor)
                    END) AS product_uom_qty,

                    SUM(CASE
                     WHEN s.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                        THEN -(l.quantity * l.price_unit_without_taxes * (100.0-COALESCE( l.discount, 0 )) / 100.0)
                        ELSE  (l.quantity * l.price_unit_without_taxes * (100.0-COALESCE( l.discount, 0 )) / 100.0)
                    END) AS sale_val,
                          
                    SUM(CASE
                     WHEN s.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                        THEN -(l.quantity * COALESCE( l.purchase_price, 0 ) )
                        ELSE  (l.quantity * COALESCE( l.purchase_price, 0 ) )
                    END) AS stock_val,

  
                   
                    
                                        
                    sum(l.commission) as commission,   
                    cu.rate,
                                                                                                  
                    s.partner_id as partner_id,
                    s.commercial_partner_id as commercial_partner_id,
                    s.user_id as user_id,
                    s.period_id,
                    s.company_id as company_id,
                    s.type, s.state , s.journal_id, s.currency_id 
        """
        return select_str
        
        

    def _from(self):
        from_str = """
                    account_invoice s
                    left join account_invoice_line l on (s.id=l.invoice_id)
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join product_uom u on (u.id=l.uos_id)
                    left join product_uom u2 on (u2.id=t.uom_id)
                    left join commission_users cu on (s.user_id = cu.user_id)
                    
        """
        return from_str

    def _where(self):
        where_str = """
              s.type in ( 'out_invoice', 'out_refund') and s.state in ( 'open','paid')
        """
        return  where_str

    def _group_by(self):
        group_by_str = """
                    l.product_id,
                    l.invoice_id,
                    t.uom_id,
                    t.categ_id,
                    s.date_invoice,
                    s.partner_id,
                    s.commercial_partner_id,
                    s.user_id,
                    cu.rate,
                    s.company_id,
                    s.period_id,
                    s.type,
                    s.state,
                    s.journal_id,
                    s.currency_id
                    
        """
        return group_by_str

 
    def init(self, cr):
        # self._table = sale_report
        tools.drop_view_if_exists(cr, self._table)
        # CREATE MATERIALIZED VIEW      
        # CREATE or REPLACE VIEW  
        sql =  """CREATE or REPLACE VIEW %s as (
            WITH currency_rate (currency_id, rate, date_start, date_end) AS (
                SELECT r.currency_id, r.rate, r.name AS date_start,
                    (SELECT name FROM res_currency_rate r2
                     WHERE r2.name > r.name AND
                           r2.currency_id = r.currency_id
                     ORDER BY r2.name ASC
                     LIMIT 1) AS date_end
                FROM res_currency_rate r
            )
            %s
            FROM
            (
                %s 
                FROM %s 
                WHERE %s 
                GROUP BY %s
            ) AS sub
            JOIN currency_rate cr ON
                (cr.currency_id = sub.currency_id AND
                 cr.date_start <= COALESCE(sub.date, NOW()) AND
                 (cr.date_end IS NULL OR cr.date_end > COALESCE(sub.date, NOW())))
        )""" 
        sql = sql  % ( self._table, self._select(),  self._sub_select(), self._from(),self._where(), self._group_by() )
        #print sql
        cr.execute(sql)
 
    
    @api.multi
    def write(self, vals):
        invoice_line = self.env['account.invoice.line'].browse(self.id)
        value = {'commission':vals.get('commission',False)}
        if invoice_line.purchase_price == 0 and invoice_line.product_id:
            if invoice_line.product_id.standard_price > 0:
                value['purchase_price'] = invoice_line.product_id.standard_price
        #if 'purchase_price' in vals:
        #    value['purchase_price'] = vals['purchase_price']
        invoice_line.write(value)
        if 'user_id' in vals:
            invoice = self.env['account.invoice'].browse(self.invoice_id)
            invoice.write({'user_id':vals['user_id']})
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

