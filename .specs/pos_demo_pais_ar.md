# Especificación Técnica para POS Demo País=AR

## Objetivo

Crear una aplicación de punto de venta (POS) demo para Argentina que cumpla con los requisitos funcionales y no funcionales establecidos en este documento.

## Alcance

### In

* País: Argentina (AR)
* Moneda: ARS
* Pagos sugeridos: efectivo, mercado_pago, transferencia, qr, tarjeta
* Facturación: afip_factura_electronica
* Facturación electrónica AFIP (CAE; tipos A/B/C según régimen)
* IVA y percepciones dependen del contribuyente

### Out

* Una aplicación de punto de venta (POS) demo que cumpla con los requisitos establecidos

## Requisitos Funcionales

1. La aplicación debe permitir la creación de órdenes de venta con los siguientes campos:
 * Fecha y hora de la venta
 * Número de orden
 * Cliente (opcional)
 * Artículos vendidos (con descripción, cantidad y precio)
 * Total de la venta
 * Forma de pago (efectivo, mercado_pago, transferencia, qr, tarjeta)
2. La aplicación debe permitir la emisión de facturas electrónicas AFIP (CAE; tipos A/B/C según régimen)
3. La aplicación debe calcular el IVA y las percepciones dependiendo del contribuyente
4. La aplicación debe permitir la impresión de la orden de venta y la factura electrónica

## Requisitos No Funcionales

1. La aplicación debe ser desarrollada utilizando el framework Vue
2. La aplicación debe ser compatible con dispositivos móviles y de escritorio
3. La aplicación debe cumplir con los estándares de seguridad y privacidad establecidos por la AFIP

## Modelo de Dominio

* Entidades principales:
 + Orden de venta
 + Cliente
 + Artículo
 + Factura electrónica
 + Forma de pago

## Integraciones

* Pagos:
 + Mercado Pago
 + Transferencia
 + QR
 + Tarjeta
* Facturación:
 + AFIP Factura Electrónica

## Criterios de Aceptación

1. La aplicación debe cumplir con los requisitos funcionales y no funcionales establecidos en este documento
2. La aplicación debe ser probada y validada por el equipo de desarrollo y el cliente
3. La aplicación debe ser documentada y entregada con un manual de usuario y un manual técnico

## Riesgos y Supuestos

* Riesgos:
 + Cambios en la legislación o regulaciones de la AFIP
 + Problemas técnicos con la integración de pagos y facturación
* Supuestos:
 + La aplicación será utilizada en un entorno de producción con un número limitado de usuarios
 + La aplicación será mantenida y actualizada regularmente para asegurar su compatibilidad y seguridad

## Notas

* La aplicación debe ser desarrollada utilizando el framework Vue y debe cumplir con los estándares de seguridad y privacidad establecidos por la AFIP.
* La aplicación debe ser probada y validada por el equipo de desarrollo y el cliente antes de su entrega.
* La aplicación debe ser documentada y entregada con un manual de usuario y un manual técnico.