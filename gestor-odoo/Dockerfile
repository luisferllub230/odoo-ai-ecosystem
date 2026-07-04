# Instancia gestora — derivada del patrón de ~/repos/odoo_pro_19 pero autocontenida:
# todo lo que necesita la imagen se copia desde esta carpeta (sin referencias al repo dev).
ARG ODOO_IMAGE=odoo
ARG ODOO_VERSION=19.0
FROM ${ODOO_IMAGE}:${ODOO_VERSION}

USER root

# Dependencias Python adicionales (mínimas para una instancia de gestión)
COPY ./requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt --break-system-packages --ignore-installed

# Entrypoint propio (sin debugpy: esto no es un entorno de desarrollo)
COPY ./entrypoint.sh /usr/bin/gestor_entrypoint.sh
COPY ./wait-for-psql.py /usr/bin/wait-for-psql.py
RUN chmod +x /usr/bin/gestor_entrypoint.sh /usr/bin/wait-for-psql.py

# Copia de la config como fallback (docker-compose la monta encima para editar sin rebuild)
COPY ./config/odoo.conf /etc/odoo/odoo.conf

# Permisos del filestore y sesiones
RUN mkdir -p /var/lib/odoo/sessions \
    && chown -R odoo:odoo /var/lib/odoo /etc/odoo

USER odoo

ENTRYPOINT ["/usr/bin/gestor_entrypoint.sh"]
CMD ["odoo"]
