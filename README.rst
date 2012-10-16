lizard-raster
==========================================

Access raster database.

Reusable parts from lizard-damage.

Installation
------------

- Include in your setup.py
- (Include in your INSTALLED_APPS)
- Add database router:

DATABASE_ROUTERS = ['lizard_raster.routers.LizardRasterRouter']

- Add raster database in settings.py (default name is 'raster')
