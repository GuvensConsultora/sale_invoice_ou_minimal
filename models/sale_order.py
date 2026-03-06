# models/sale_order.py
# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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

    def _empresa_usa_uo(self):
        """True si la empresa del pedido tiene al menos una UO configurada.
        Por qué: empresas como la S.H. no usan UO. Toda la lógica de UO
        debe saltearse para evitar errores de acceso (ir.rules)."""
        company = self.company_id or self.env.company
        return bool(self.env["operating.unit"].sudo().search_count([
            ("company_id", "=", company.id),
        ]))

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

    @api.model
    def _register_hook(self):
        """Limpia operating_unit_id de pedidos cuya UO no pertenece a su empresa.
        Por qué: pedidos existentes de la S.H. tienen UO de 'Lupatini y CIA'
        cargada por el default anterior. Las ir.rules de operating_unit bloquean
        la lectura → error 'no tiene acceso leer Unidad Operativa'.
        Se ejecuta en cada startup para cubrir DB persistentes (Odoo.sh staging)."""
        self.env.cr.execute("""
            UPDATE sale_order so
            SET operating_unit_id = NULL
            FROM operating_unit ou
            WHERE so.operating_unit_id = ou.id
              AND so.company_id != ou.company_id
        """)
        if self.env.cr.rowcount:
            _logger.info(
                "sale_invoice_ou_minimal: limpiados %d pedidos con UO de otra empresa",
                self.env.cr.rowcount,
            )
        return super()._register_hook()
