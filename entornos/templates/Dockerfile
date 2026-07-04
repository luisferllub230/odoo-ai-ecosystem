# odoo-ai-ecosystem / entornos — version-parametrized Odoo dev image.
# ODOO_VERSION comes from docker-compose build args (e.g. "17.0", "19.0").
ARG ODOO_VERSION=19.0
FROM odoo:${ODOO_VERSION}

# Run installs as root, drop back to the unprivileged odoo user at the end.
# Do NOT re-elevate with `user: root` in docker-compose (audit gotcha 4):
# it breaks filestore ownership.
USER root

# Re-declare so the ARG is visible in this build stage.
ARG ODOO_VERSION

# --- Extra python deps -------------------------------------------------------
# debugpy is mandatory: entrypoint.sh always launches Odoo under it.
# Project-specific deps belong to the project repo, not to this base file.
COPY ./requirements.txt /tmp/requirements.txt

# Odoo >= 18 images ship a PEP 668 "externally managed" Python and need
# --break-system-packages --ignore-installed. Older images (<= 17, Py 3.10)
# use classic pip with upgraded pip/setuptools first.
RUN MAJOR="${ODOO_VERSION%%.*}" && \
    if [ "$MAJOR" -ge 18 ]; then \
        pip3 install -r /tmp/requirements.txt --break-system-packages --ignore-installed; \
    else \
        pip3 install --upgrade pip setuptools && \
        pip3 install -r /tmp/requirements.txt; \
    fi

# --- Custom entrypoint ---------------------------------------------------------
# Wraps the default Odoo entrypoint with `debugpy --listen 0.0.0.0:3001` so
# the IDE can attach. See .vscode/launch.json on the host side.
COPY ./entrypoint.sh /usr/bin/odoo_dev_entrypoint.sh
COPY ./wait-for-psql.py /usr/local/bin/wait-for-psql.py
RUN chmod +x /usr/bin/odoo_dev_entrypoint.sh /usr/local/bin/wait-for-psql.py

# Ensure filestore dirs exist and are writable by the unprivileged odoo user.
RUN mkdir -p /var/lib/odoo/sessions && chown -R odoo:odoo /var/lib/odoo

USER odoo

ENTRYPOINT ["/usr/bin/odoo_dev_entrypoint.sh"]
CMD ["odoo"]
