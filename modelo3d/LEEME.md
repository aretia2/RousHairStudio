# Rou's Hair Studio: modelo 3D, versión 1

- `rou_studio.glb`: el modelo descargable. Se abre en Blender, en el visor 3D de Windows o en <https://gltf-viewer.donmccurdy.com>.
- `index.html` + `serve.py`: el visor web con las vistas predefinidas. Se arranca con `python modelo3d/serve.py 5198` y se abre `http://localhost:5198`.
- `renders/`: 10 renders PNG (1920×1080; la planta es vertical).
- `build_model.py`: el generador paramétrico. Todas las medidas están arriba del archivo; se cambian y se vuelve a ejecutar.

## Fuentes
Solo video1.mp4 (fachada) y video2.mp4 (recorrido interior). Las historias de Instagram están desactualizadas y no se han usado.

## Medidas deducidas (no medidas en el local)
| Elemento | Valor | Cómo se ha deducido |
|---|---|---|
| Ancho interior | 6,5 m | escaparate (≈4,8 m) + puerta (≈1,1 m) + machones; alturas de persona en video1 |
| Fondo interior | 16 m | 5 sillones mostaza a ≈1,2 m + 3 puestos de barbería + zona de lavado (plano largo, s. 33–35 de video2) |
| Techo blanco / techo negro | 3,0 m / 2,8 m | escalón visible entre las dos zonas |
| Zona de techo negro | primeros 4 m | video1 y s. 31–33 de video2 |
| Desnivel acera–local | 15 cm, con rampa de 1,3 m frente a la puerta | video1, s. 2–3 |
| Altura del escaparate | 2,75 m + banda negra de 0,7 m | |

## Supuestos (no se ven en el material)
- La planta superior del edificio y los machones laterales: son genéricos.
- El interior de la puerta gris del fondo (aseo o almacén) no está modelado.
- La pared de enfrente de los puestos de barbería en la zona negra: se ha supuesto la recepción de lamas y la planta alta.
- Se ha omitido la barandilla de la acera.
