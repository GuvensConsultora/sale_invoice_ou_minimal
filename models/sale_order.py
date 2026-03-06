# models/sale_order.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = "sale.order"


    operating_unit_id = fields.Many2one(
        "operating.unit",
        string="Unidad Operativa",
        default=lambda self: self._default_operating_unit(),
        tracking=True,
        help="Unidad Operativa que se usará al crear la factura.",
    )

    @api.model
    def _default_operating_unit(self):
        """Default UO solo si la empresa actual tiene UO configuradas.
        Por qué: en multi-company, algunas empresas no usan UO (ej: S.H.).
        Si el usuario tiene UO de otra empresa como default, no debe
        arrastrarse a pedidos de una empresa sin UO."""
        ou = self.env.user.default_operating_unit_id
        if ou and ou.company_id == self.env.company:
            return ou
        return False

    def _prepare_invoice(self):
        """Odoo 17: inyecta UO y diario coherentes en la factura.
        Por qué: si el pedido no tiene UO (empresa sin UO), se salta
        la lógica de UO y deja que Odoo use el diario por defecto."""
        self.ensure_one()
        vals = super()._prepare_invoice()

        # Por qué: si no hay UO en el pedido, la empresa no usa UO → flujo nativo Odoo
        ou = self.operating_unit_id
        if not ou:
            return vals

        # Inyectar UO a la factura
        vals["operating_unit_id"] = ou.id

        # Encontrar diario de ventas que coincida con UO y compañía
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
