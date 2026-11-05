#!/bin/sh
# Renders finales 1920x1080 (Cycles CPU)
B="/c/Program Files/Blender Foundation/Blender 5.2/blender.exe"
cd "$(dirname "$0")"
"$B" -b -P render_cycles.py -- entrada 1920 1080 160 "$PWD/renders_realistas/entrada.png" --save-blend 2>&1 | grep -E "RENDER_OK|Error|Traceback"
for v in fondo fachada barberia; do
  "$B" -b -P render_cycles.py -- $v 1920 1080 160 "$PWD/renders_realistas/$v.png" 2>&1 | grep -E "RENDER_OK|Error|Traceback"
done
