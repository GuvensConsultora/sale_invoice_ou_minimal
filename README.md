# sale_invoice_ou_minimal

Módulo para **Odoo 17** que hace fluir la **Unidad Operativa (Operating Unit, OU)** desde el usuario → presupuesto de venta → líneas → factura, y fuerza el uso de un **diario** compatible con esa OU al crear la factura (incluida la creación desde el *wizard* de facturación de ventas).

---

## Objetivo

- Agregar `operating_unit_id` al modelo `sale.order` (por defecto tomado de `res.users.default_operating_unit_id`).
- Propagar la OU a `sale.order.line` como campo *related* (almacenado).
- Al preparar la factura (`_prepare_invoice`), **establecer `operating_unit_id`** en el `account.move` resultante.
- Al crear la factura, **elegir un diario de cliente (`account.journal`) cuya OU coincida**.  
  Si no existe, levantar un **UserError** claro.

> El módulo **no** agrega reglas de seguridad nuevas: se apoya en `operating_unit` y `account_operating_unit` (OCA).

---

## Características

- Campo **visible y editable** en Presupuesto: `sale.order.operating_unit_id`.
- Campo técnico **en líneas**: `sale.order.line.operating_unit_id` (related + store).
- Integración con el **wizard de facturación** de ventas: respeta OU y diario.
- **UserError** si:
  - No hay diario de “Facturas de cliente” con la misma OU.
  - El diario seleccionado no coincide con la OU del movimiento (protege de desbalances con OCA OU).

---

## Dependencias

- `sale`
- `account`
- `operating_unit` (OCA)
- `account_operating_unit` (OCA)

---

## Instalación

1. Copiar el directorio del módulo a tus `addons_path`.
2. Actualizar la lista de apps.
3. Instalar **sale_invoice_ou_minimal**.

> Si ya tenés presupuestos creados, tras instalar conviene **abrir y guardar** (o ejecutar una **actualización del módulo**) para rellenar `operating_unit_id` según el valor por defecto del usuario.

---

## Configuración

1. En cada **usuario**: definir **Unidad Operativa por defecto**  
   `Ajustes > Usuarios > [Usuario] > Unidad Operativa por defecto`.
2. En **Diarios de cliente**: asignar **Unidad Operativa**  
   `Contabilidad > Configuración > Diarios > [Factura de cliente] > Unidad operativa`.

**Checklist rápido**  
- [ ] `res.users.default_operating_unit_id` seteado.  
- [ ] Diarios con `type = sale` tienen `operating_unit_id` asignado.  
- [ ] El partner / impuestos / cuentas están correctos para emitir.

---

## Uso

1. Crear un **Presupuesto de venta**. El campo **Unidad Operativa** se autocompleta desde el usuario, pero podés cambiarlo.
2. Confirmar o facturar desde el **wizard de anticipo / facturación**.
3. Se generará la **Factura** con:
   - `account.move.operating_unit_id` = OU del pedido.
   - Diario elegido con `operating_unit_id` = OU del pedido.
4. Publicar la factura normalmente.

---

## Detalles técnicos

### Modelos y campos

- `sale.order`
  - `operating_unit_id = fields.Many2one('operating.unit', default=_default_from_user, index=True, required=True)`
- `sale.order.line`
  - `operating_unit_id = fields.Many2one(related='order_id.operating_unit_id', store=True, index=True, readonly=True)`

### Hooks principales

- `sale.order._prepare_invoice(vals)`:
  - Inserta `operating_unit_id` en `vals` del `account.move`.
  - Si el contexto/vals no traen diario, busca uno de tipo **sale** con la **misma OU**.
  - Si no se encuentra diario compatible, **UserError** con guía de corrección.

*(El módulo de OCA ya chequea consistencia OU en diario y asiento; aquí ayudamos a **elegir bien el diario** para no romper).*

### Búsqueda de diario (dominio sugerido)

```python
[
  ('type', '=', 'sale'),
  ('company_id', '=', company_id_del_pedido),
  ('operating_unit_id', '=', OU),
]
```

> Recomendación: **asignar OU siempre** a los diarios de ventas.

---

## Mensajes de error (UserError)

- **“No se encontró un Diario de cliente con la misma Unidad Operativa que el pedido.”**  
  *Acción sugerida:* Asigne la OU al diario **Facturas de cliente** o cree uno nuevo para esa OU.

- **“El Diario seleccionado no coincide con la Unidad Operativa del movimiento.”**  
  *Acción sugerida:* Cambie el diario por uno de la misma OU.

---

## Cómo saber que funciona

- En el Presupuesto, el campo **Unidad Operativa** aparece y queda guardado.
- Al facturar, la **Factura** hereda la OU del pedido.
- El **Diario** en la factura corresponde a la **misma OU**.
- No aparecen errores del tipo:
  - *“The OU in the Move and in Journal must be the same.”*
  - *“Invalid field ...operating_unit_id in leaf ...”*

---

## Compatibilidad

- **Odoo 17** (Enterprise / Community)  
- Depende de OCA: `operating_unit`, `account_operating_unit` (v17).

---

## Desinstalación

- No elimina datos de facturas ya creadas.
- Elimina los campos agregados al desinstalar.
- Si tenías reglas de récord que dependían de `sale.order.line.operating_unit_id`, revísalas antes de desinstalar.

---

## Limitaciones conocidas

- Si existen **múltiples diarios** de cliente por compañía y OU, la selección toma el primero según orden por defecto. Podés ajustar el dominio/orden si necesitás criterios adicionales (secuencia, nombre, etc.).

---

## Changelog

- **1.0.0**
  - Campo `operating_unit_id` en `sale.order`.
  - Campo related `operating_unit_id` en `sale.order.line` (store).
  - Herencia de `_prepare_invoice` para setear OU en factura y elegir diario por OU.
  - UserError claros ante inconsistencias.

---

## Mantenimiento

- Autor: Cerdá Horacio.
- Partner: Güvens
- Licencia: LGPL-3
- Issues y PRs: repositorio del proyecto
