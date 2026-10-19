# Pomelo · sistema de diseño

Dirección: herramienta de escritorio sobria y cálida. Superficies grafito (o marfil en modo claro),
un único acento cítrico y color solo para identificar el tipo de archivo.

## Tokens (pomelo/ui/theme.py)
- Superficies: bg → surface → surface2 → elevated (cada nivel un paso más claro en oscuro).
- Texto: text / text2 (secundario) / text3 (terciario). Contraste ≥ 4,5:1 sobre surface en ambos temas.
- Acento: #FF7A45 (oscuro) / #E85A26 (claro), siempre con texto oscuro encima (≥ 5:1).
- Color por tipo de archivo (GROUPS): imagen naranja, audio violeta, vídeo rojo, documentos azul,
  PDF rosa, hojas verde, presentaciones amarillo, comprimidos tierra, acciones gris azulado.

## Tipografía
Segoe UI Variable (Display para títulos, Text para cuerpo). Jerarquía por peso + tamaño:
título 15–17 pt semibold, cuerpo 10 pt, secundario 9 pt, sobrelínea 8,5 pt en mayúsculas.

## Forma
Radios: 20 (zona de soltar), 16 (popovers), 14 (tarjetas), 10–11 (controles), 7 (píldoras).
Iconos vectoriales propios de trazo 1,8 en rejilla de 24 (pomelo/ui/icons.py). Sin emojis.

## Movimiento
- Aparición de popovers y rueda: 180–200 ms, ease-out (OutCubic/OutQuint), desde escala 0,9–0,97.
- Salidas más rápidas que entradas (150 ms).
- Hover de la rueda: aproximación exponencial por fotograma, interrumpible desde el valor actual.
- Si Windows tiene desactivadas las animaciones, todas las duraciones pasan a 0 (theme.ms).

## Accesibilidad
Anillo de foco visible solo con teclado (TabFocus), selector navegable con flechas/Intro/Tab/Esc,
nombres accesibles en botones de icono, estados no transmitidos solo por color (iconos ✓ / ✕ / candado).
