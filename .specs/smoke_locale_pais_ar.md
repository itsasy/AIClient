# Especificación Técnica para Smoke Locale País=AR
=============================================

## Objetivo
-----------

Crear una especificación técnica clara y completa para la implementación de smoke locale en el país de Argentina (AR).

## Alcance (in / out)
--------------------

* Entradas:
 + País: Argentina (AR)
 + Moneda: ARS
 + Pagos sugeridos: efectivo, mercado_pago, transferencia, qr, tarjeta
 + Facturación: afip_factura_electronica
* Salidas:
 + Especificación técnica para la implementación de smoke locale en Argentina (AR)

## Requisitos Funcionales
-------------------------

1. La aplicación debe permitir la selección del país y la moneda correspondiente.
2. La aplicación debe integrar los pagos sugeridos para Argentina (AR).
3. La aplicación debe implementar la facturación electrónica AFIP (CAE) según el régimen del contribuyente.
4. La aplicación debe calcular el IVA y las percepciones correspondientes según el contribuyente.

## Requisitos No Funcionales
---------------------------

1. La aplicación debe ser compatible con el framework Vue.
2. La aplicación debe cumplir con las normas de seguridad y privacidad para la protección de datos de los usuarios.

## Modelo de Dominio (Entidades Principales)
-----------------------------------------

* País
* Moneda
* Pago
* Facturación
* Contribuyente
* IVA
* Percepciones

## Integraciones (Pagos, Facturación, Terceros)
--------------------------------------------

* Pagos:
 + Efectivo
 + Mercado Pago
 + Transferencia
 + QR
 + Tarjeta
* Facturación:
 + AFIP Factura Electrónica (CAE)
* Terceros:
 + No se especifican terceros en el LOCALE.

## Criterios de Aceptación
-------------------------

1. La aplicación debe permitir la selección del país y la moneda correspondiente.
2. La aplicación debe integrar los pagos sugeridos para Argentina (AR).
3. La aplicación debe implementar la facturación electrónica AFIP (CAE) según el régimen del contribuyente.
4. La aplicación debe calcular el IVA y las percepciones correspondientes según el contribuyente.

## Riesgos y Supuestos
----------------------

* Riesgos:
 + No se especifican riesgos en el LOCALE.
* Supuestos:
 + Se asume que la aplicación se implementará en un entorno seguro y privado.
 + Se asume que la aplicación cumplirá con las normas de seguridad y privacidad para la protección de datos de los usuarios.