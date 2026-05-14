FROM moisesbm/ipscuidando:v1

# 1. Borramos el index por defecto de Nginx por si acaso
RUN rm -f /usr/share/nginx/html/index.html

# 2. Copiamos el contenido de la subcarpeta 'browser' a la raíz
# Usamos un truco de shell para asegurar que se muevan incluso archivos ocultos
RUN cp -r /usr/share/nginx/html/browser/. /usr/share/nginx/html/

# 3. Limpiamos la carpeta browser para que no ocupe espacio doble
RUN rm -rf /usr/share/nginx/html/browser

# 4. Aseguramos que Nginx tenga permisos
RUN chmod -R 755 /usr/share/nginx/html