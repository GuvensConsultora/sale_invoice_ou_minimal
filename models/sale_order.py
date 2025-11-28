# models/sale_order.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"


    operating_unit_id = fields.Many2one(
        "operating.unit",
        string="Unidad Operativa",
        default=lambda self: self.env.user.default_operating_unit_id,
        tracking=True,
        help="Unidad Operativa que se usará al crear la factura.",
    )


    def _prepare_invoice(self):
        """
        Odoo 17:
        - PRIORIDAD 1: usar sale.order.operating_unit_id si está seteada.
        - PRIORIDAD 2: fallback a res.users.default_operating_unit_id.
        - Elegir diario de ventas activo de la misma compañía con esa UO.
        - Si no existe diario compatible, lanzar UserError claro.
        """
        self.ensure_one()
        vals = super()._prepare_invoice()

        # 1) Resolver UO efectiva
        ou = self.operating_unit_id or self.env.user.default_operating_unit_id
        if not ou:
            raise UserError(_(
                "No se puede crear la factura: ni el pedido ni el usuario tienen Unidad Operativa.\n"
                "Cargue 'Unidad Operativa' en el pedido o configure una por defecto en el usuario."
            ))

        # 2) Inyectar UO a la factura
        vals["operating_unit_id"] = ou.id

        # 3) Encontrar diario de ventas que coincida con UO y compañía
        company = self.company_id or self.env.company
        journal = self.env["account.journal"].sudo().search([
            ("type", "=", "sale"),
            ("company_id", "=", company.id),
            ("operating_unit_id", "=", ou.id),
            ("active", "=", True),
        ], limit=1)

        if not journal:
            raise UserError(_(
                "No existe un Diario de Ventas activo para la compañía '%s' con la Unidad Operativa '%s'.\n"
                "Cree o configure un diario de tipo 'Ventas' con esa UO para poder facturar."
            ) % (company.display_name, ou.display_name))

        vals["journal_id"] = journal.id
        return vals
