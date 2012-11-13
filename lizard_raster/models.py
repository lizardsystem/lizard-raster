# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
from __future__ import unicode_literals

import logging

from django.conf import settings
from django.contrib.gis.db import models
# from django.utils.translation import ugettext_lazy as _

from lizard_raster import raster

from osgeo import gdal

logger = logging.getLogger(__name__)


class AhnIndex(models.Model):
    """
    Index for finding AHN codes.

    From lizard-damage.

    Sql for this table can be generated using:

    shp2pgsql -s 28992 ahn2_05_int_index public.data_index | sed\
    s/geom/the_geom/g > index.sql

    Table definition can be obtained by executing this sql and using
    bin/django inspectdb, and then replace DecimalFields by FloatFields
    """
    gid = models.IntegerField(primary_key=True)
    x = models.FloatField(null=True, blank=True)  # In RD
    y = models.FloatField(null=True, blank=True)
    cellsize = models.CharField(max_length=2, blank=True)
    lo_x = models.CharField(max_length=6, blank=True)
    lo_y = models.CharField(max_length=6, blank=True)
    bladnr = models.CharField(max_length=24, blank=True)
    update = models.DateField(null=True, blank=True)
    datum = models.DateField(null=True, blank=True)
    min_datum = models.DateField(null=True, blank=True)
    max_datum = models.DateField(null=True, blank=True)
    ar = models.FloatField(null=True, blank=True)
    the_geom = models.MultiPolygonField(srid=28992, null=True, blank=True)  # All squares?
    objects = models.GeoManager()

    class Meta:
        db_table = 'data_index'

    def __unicode__(self):
        return '%s' % (self.bladnr)

    # def extent_wgs84(self, e=None):
    #     if e is None:
    #         e = self.the_geom.extent
    #     #x0, y0 = coordinates.rd_to_wgs84(e[0], e[1])
    #     #x1, y1 = coordinates.rd_to_wgs84(e[2], e[3])
    #     x0, y0 = transform(rd_proj, wgs84_proj, e[0], e[1])
    #     x1, y1 = transform(rd_proj, wgs84_proj, e[2], e[3])
    #     #print ('Converting RD %r to WGS84 %s' % (e, '%f %f %f %f' % (x0, y0, x1, y1)))
    #     # we're using it for google maps and it does not project exactly on the correct spot.. try to fix it ugly
    #     # add rotation = 0.9 too for the kml
    #     #x0 = x0 - 0.00012
    #     #y0 = y0 + 0.000057
    #     #x1 = x1 + 0.000154
    #     #y1 = y1 - 0.000051
    #     return (x0, y0, x1, y1)

    def get_ds(self, tablename='data_ahn'):
        """
        Get dataset for this tile.

        tablename is data_ahn or data_lgn
        """
        driver = 'PostGISRaster'
        tilename = self.bladnr

        gdal.GetDriverByName(str(driver))
        open_argument = raster.get_postgisraster_argument(
            tablename, tilename,
        )

        dataset = gdal.Open(str(open_argument))

        logger.debug('Opening dataset: %s', open_argument)

        # PostGISRaster driver in GDAL 1.9.1 sets nodatavalue to 0.
        # In that case we get it from the database
        if (dataset is not None and
            dataset.GetRasterBand(1).GetNoDataValue() == 0):
            nodatavalue = raster.get_postgisraster_nodatavalue(
                tablename, tilename,
            )
            dataset.GetRasterBand(1).SetNoDataValue(nodatavalue)

        return dataset


    @classmethod
    def get_ahn_indices(cls, ds=None, polygon=None):
        """ Return the ahn index objects that cover this dataset. """
        if polygon is None:
            polygon = raster.get_polygon(ds)
        ahn_indices = cls.objects.filter(
            the_geom__intersects=polygon,
            )
        return ahn_indices
